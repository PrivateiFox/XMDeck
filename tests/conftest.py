"""Pytest fixtures and test data generators for XMDeck."""

from __future__ import annotations

import pytest

from backend.protocol.framing import (
    ALT_END_MARKER,
    ALT_START_MARKER,
    END_MARKER,
    START_MARKER,
    encode_frame,
)
from backend.protocol.messages import FrameDataType


@pytest.fixture
def sample_payload() -> bytes:
    """Return an unescaped payload containing control characters."""
    return b"SonyMDR\x3c\x3d\x3e\x00\xffTestPayload"


@pytest.fixture
def valid_standard_frame(sample_payload: bytes) -> bytes:
    """Return a valid encoded frame with standard Sony delimiters."""
    return encode_frame(
        data_type=FrameDataType.DATA_MDR,
        seq=0,
        payload=sample_payload,
        start_marker=START_MARKER,
        end_marker=END_MARKER,
    )


@pytest.fixture
def valid_alt_frame(sample_payload: bytes) -> bytes:
    """Return a valid encoded frame with inverted delimiters."""
    return encode_frame(
        data_type=FrameDataType.DATA_MDR,
        seq=1,
        payload=sample_payload,
        start_marker=ALT_START_MARKER,
        end_marker=ALT_END_MARKER,
    )
