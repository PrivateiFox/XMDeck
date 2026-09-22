"""Sony MDR Protocol V2 framing, byte escaping, and checksum calculations.

Pure Python implementation completely decoupled from I/O for 100% unit-testability.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

# Canonical Sony MDR V2 Delimiters (on-the-wire format)
START_MARKER: int = 0x3E  # '>'
END_MARKER: int = 0x3C  # '<'
ESCAPE_SENTRY: int = 0x3D  # '='

# Alternate/inverted delimiters (e.g. for testing or specification variants)
ALT_START_MARKER: int = 0x3C  # '<'
ALT_END_MARKER: int = 0x3E  # '>'

# Escaped values: byte - 0x10
ESCAPED_3C: int = 0x2C  # 0x3C - 0x10 = 0x2C (44)
ESCAPED_3D: int = 0x2D  # 0x3D - 0x10 = 0x2D (45)
ESCAPED_3E: int = 0x2E  # 0x3E - 0x10 = 0x2E (46)

SPECIAL_BYTES: frozenset[int] = frozenset({0x3C, 0x3D, 0x3E})

# Minimum unescaped frame size: 1B type + 1B seq + 4B length + 0B payload + 1B checksum = 7B
MIN_UNESCAPED_FRAME_LEN: int = 7


class FramingError(Exception):
    """Raised when frame parsing, unescaping, or checksum validation fails."""


@dataclass(frozen=True, slots=True)
class Frame:
    """Represents a decoded Sony MDR V2 protocol frame."""

    data_type: int
    seq: int
    payload: bytes


def calc_checksum(data: bytes) -> int:
    """Calculate the Sony MDR V2 8-bit additive checksum over unescaped bytes."""
    return sum(data) & 0xFF


def escape_bytes(data: bytes) -> bytes:
    """Escape special Sony MDR control bytes (0x3C, 0x3D, 0x3E).

    Each special byte `b` is replaced by `0x3D` followed by `(b - 0x10)`.
    """
    out = bytearray()
    for b in data:
        if b in SPECIAL_BYTES:
            out.append(ESCAPE_SENTRY)
            out.append(b - 0x10)
        else:
            out.append(b)
    return bytes(out)


def unescape_bytes(data: bytes) -> bytes:
    """Unescape a Sony MDR escaped byte sequence.

    Any byte immediately following `0x3D` is restored with `(byte + 0x10)`.

    Raises:
        FramingError: If a dangling escape byte is found or an invalid byte follows 0x3D.
    """
    out = bytearray()
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if b == ESCAPE_SENTRY:
            if i + 1 >= length:
                raise FramingError("Dangling escape byte at end of buffer")
            i += 1
            next_b = data[i]
            restored = next_b + 0x10
            if restored not in SPECIAL_BYTES:
                raise FramingError(
                    f"Invalid escaped byte 0x{next_b:02X} (restores to 0x{restored:02X})"
                )
            out.append(restored)
        else:
            out.append(b)
        i += 1
    return bytes(out)


def encode_frame(
    data_type: int,
    seq: int,
    payload: bytes,
    start_marker: int = START_MARKER,
    end_marker: int = END_MARKER,
) -> bytes:
    """Encode payload into a framed Sony MDR V2 packet.

    Format before escaping:
        [data_type (1B), seq & 1 (1B), payload_length (4B BE), payload (NB), checksum (1B)]
    Packet on wire:
        start_marker + escape(unescaped_data) + end_marker
    """
    header = struct.pack(">BBI", data_type & 0xFF, seq & 0x01, len(payload))
    body = header + payload
    checksum = calc_checksum(body)
    unescaped = body + bytes([checksum])
    escaped = escape_bytes(unescaped)
    return bytes([start_marker]) + escaped + bytes([end_marker])


def decode_frame(
    raw_packet: bytes,
    start_marker: int = START_MARKER,
    end_marker: int = END_MARKER,
) -> Frame:
    """Decode a single complete Sony MDR V2 packet.

    Args:
        raw_packet: The raw byte packet including delimiters.
        start_marker: Expected packet start byte.
        end_marker: Expected packet end byte.

    Returns:
        Frame with parsed data_type, seq, and payload.

    Raises:
        FramingError: If delimiters, unescaping, length, or checksum are invalid.
    """
    if len(raw_packet) < 2:
        raise FramingError(f"Packet too short ({len(raw_packet)} bytes)")

    if raw_packet[0] != start_marker:
        raise FramingError(
            f"Invalid start delimiter 0x{raw_packet[0]:02X}, expected 0x{start_marker:02X}"
        )
    if raw_packet[-1] != end_marker:
        raise FramingError(
            f"Invalid end delimiter 0x{raw_packet[-1]:02X}, expected 0x{end_marker:02X}"
        )

    escaped_body = raw_packet[1:-1]
    unescaped = unescape_bytes(escaped_body)

    if len(unescaped) < MIN_UNESCAPED_FRAME_LEN:
        raise FramingError(
            f"Unescaped frame too short ({len(unescaped)} < {MIN_UNESCAPED_FRAME_LEN})"
        )

    expected_checksum = unescaped[-1]
    actual_checksum = calc_checksum(unescaped[:-1])
    if actual_checksum != expected_checksum:
        raise FramingError(
            f"Checksum mismatch: expected 0x{expected_checksum:02X}, "
            f"calculated 0x{actual_checksum:02X}"
        )

    data_type, seq, payload_length = struct.unpack(">BBI", unescaped[:6])
    payload = unescaped[6:-1]

    if len(payload) != payload_length:
        raise FramingError(
            f"Payload length mismatch: header specifies {payload_length}, got {len(payload)}"
        )

    return Frame(data_type=data_type, seq=seq, payload=payload)


class StreamParser:
    """Stream parser that buffers incoming byte chunks and extracts valid frames."""

    def __init__(
        self,
        start_marker: int = START_MARKER,
        end_marker: int = END_MARKER,
        max_buffer_size: int = 65536,
    ) -> None:
        self._buffer = bytearray()
        self._start_marker = start_marker
        self._end_marker = end_marker
        self._max_buffer_size = max_buffer_size

    def reset(self) -> None:
        """Clear internal buffer."""
        self._buffer.clear()

    @property
    def buffer(self) -> bytes:
        """Return the current unparsed buffer content."""
        return bytes(self._buffer)

    def feed(self, chunk: bytes) -> list[Frame]:
        """Feed incoming stream bytes and return any complete, verified frames.

        Any malformed framing or corrupted bytes are skipped cleanly.
        """
        self._buffer.extend(chunk)
        if len(self._buffer) > self._max_buffer_size:
            # Prevent memory exhaustion on endless corrupted stream
            self._buffer.clear()
            return []

        frames: list[Frame] = []

        while True:
            # Find the start marker
            start_idx = self._buffer.find(self._start_marker)
            if start_idx == -1:
                # No start marker found, discard all data
                self._buffer.clear()
                break

            if start_idx > 0:
                # Discard noise preceding the start marker
                del self._buffer[:start_idx]

            # Find the next end marker after the start marker
            end_idx = -1
            # We must be careful not to treat an escaped end marker as a real delimiter,
            # though by protocol definition an end marker inside payload is escaped as 0x3D 0x2C.
            for i in range(1, len(self._buffer)):
                if self._buffer[i] == self._end_marker:
                    end_idx = i
                    break

            if end_idx == -1:
                # Incomplete frame, wait for more data
                break

            # Candidate frame bytes: self._buffer[: end_idx + 1]
            candidate = bytes(self._buffer[: end_idx + 1])
            del self._buffer[: end_idx + 1]

            try:
                frame = decode_frame(
                    candidate,
                    start_marker=self._start_marker,
                    end_marker=self._end_marker,
                )
                frames.append(frame)
            except FramingError:
                # Discard corrupted candidate and search for next frame
                continue

        return frames
