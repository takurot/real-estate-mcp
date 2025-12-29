"""GIS helper utilities for MVT/PBF encoding and coordinate transformations."""

from __future__ import annotations

import base64


def encode_mvt_to_base64(content: bytes) -> str:
    """
    Encode MVT/PBF binary data to base64 string.

    Args:
        content: Binary MVT/PBF data

    Returns:
        Base64-encoded string
    """
    return base64.b64encode(content).decode("ascii")


def decode_base64_to_mvt(encoded: str) -> bytes:
    """
    Decode base64 string back to MVT/PBF binary data.

    Args:
        encoded: Base64-encoded string

    Returns:
        Binary MVT/PBF data
    """
    return base64.b64decode(encoded)


__all__ = ["encode_mvt_to_base64", "decode_base64_to_mvt"]
