from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, MutableMapping


ClockFn = Callable[[], float]


@dataclass(slots=True)
class _MemoryEntry:
    value: Any
    expires_at: float


class InMemoryTTLCache:
    """Simple TTL-based LRU cache for small JSON payloads."""

    def __init__(self, maxsize: int, ttl: float, clock: ClockFn | None = None) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self._maxsize = maxsize
        self._ttl = ttl
        self._clock: ClockFn = clock or time.monotonic
        self._store: "OrderedDict[str, _MemoryEntry]" = OrderedDict()

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if not entry:
            return None
        if self._clock() >= entry.expires_at:
            self._delete(key)
            return None
        self._store.move_to_end(key)
        return entry.value

    def set(self, key: str, value: Any) -> None:
        expires_at = self._clock() + self._ttl
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = _MemoryEntry(value=value, expires_at=expires_at)
        self._evict_if_needed()

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)

    def _evict_if_needed(self) -> None:
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)

    def _delete(self, key: str) -> None:
        self._store.pop(key, None)


@dataclass(slots=True)
class _FileEntry:
    path: Path
    expires_at: float


class BinaryFileCache:
    """Persist binary payloads to disk with TTL-based invalidation."""

    def __init__(
        self,
        directory: Path | str,
        ttl_seconds: float = 6 * 60 * 60,
        clock: ClockFn | None = None,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._ttl = ttl_seconds
        self._clock: ClockFn = clock or time.monotonic
        self._entries: MutableMapping[str, _FileEntry] = {}

    def set(self, key: str, content: bytes, suffix: str = ".bin") -> Path:
        suffix = suffix if suffix.startswith(".") else f".{suffix}"
        path = self._directory / f"{self._digest(key)}{suffix}"
        path.write_bytes(content)
        expires_at = self._clock() + self._ttl
        self._entries[key] = _FileEntry(path=path, expires_at=expires_at)
        return path

    def get(self, key: str) -> Path | None:
        entry = self._entries.get(key)
        if not entry:
            return None
        if self._clock() >= entry.expires_at or not entry.path.exists():
            self._evict(key, entry.path)
            return None
        return entry.path

    def purge_expired(self) -> None:
        to_remove = [
            key
            for key, entry in self._entries.items()
            if self._clock() >= entry.expires_at or not entry.path.exists()
        ]
        for key in to_remove:
            path = self._entries[key].path
            self._evict(key, path)

    def clear(self) -> None:
        for entry in list(self._entries.values()):
            if entry.path.exists():
                try:
                    entry.path.unlink()
                except OSError:
                    pass
        self._entries.clear()

    def _evict(self, key: str, path: Path) -> None:
        self._entries.pop(key, None)
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass

    @staticmethod
    def _digest(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()
