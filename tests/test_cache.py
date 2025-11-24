from pathlib import Path

import pytest

from mlit_mcp.cache import BinaryFileCache, InMemoryTTLCache


class ManualClock:
    def __init__(self, start: float = 0.0) -> None:
        self._value = start

    def advance(self, seconds: float) -> None:
        self._value += seconds

    def __call__(self) -> float:
        return self._value


def test_in_memory_cache_entry_expires_after_ttl() -> None:
    clock = ManualClock()
    cache = InMemoryTTLCache(maxsize=4, ttl=5, clock=clock)
    cache.set("foo", {"value": 1})
    assert cache.get("foo") == {"value": 1}

    clock.advance(6)
    assert cache.get("foo") is None


def test_binary_cache_writes_files_and_expires(tmp_path: Path) -> None:
    clock = ManualClock()
    cache = BinaryFileCache(tmp_path / "bin", ttl_seconds=5, clock=clock)

    path = cache.set("bar", b"payload", suffix=".bin")
    assert path.exists()
    assert path.read_bytes() == b"payload"
    assert cache.get("bar") == path

    clock.advance(6)
    assert cache.get("bar") is None
    assert not path.exists()

