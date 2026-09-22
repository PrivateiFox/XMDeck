"""Stop-and-Wait Alternating-Bit ARQ state machine for Sony MDR V2.

Sony MDR V2 uses a 1-bit alternating sequence counter (0 or 1).
- Every outbound command with sequence `S` requires an ACK/response with sequence `1 - S`.
- Every inbound data frame with sequence `S` requires transmitting an ACK frame with `1 - S`.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable

from .framing import Frame, encode_frame
from .messages import FrameDataType


class ARQTimeoutError(Exception):
    """Raised when an outbound frame is not acknowledged within the retry limit."""


def is_ack_required(data_type: int) -> bool:
    """Return True if incoming frame data type requires sending an ACK."""
    return data_type in (FrameDataType.DATA_MDR, FrameDataType.DATA_MDR_NO2)


def invert_seq(seq: int) -> int:
    """Invert the 1-bit sequence counter (0 -> 1, 1 -> 0)."""
    return (1 - seq) & 0x01


@dataclass
class OutboundTransaction:
    """Tracks state of an active outbound command awaiting acknowledgement."""

    frame: Frame
    encoded_bytes: bytes
    expected_ack_seq: int
    retries_left: int
    future: asyncio.Future[None] | None = None


class ARQStateMachine:
    """Pure synchronous ARQ state machine tracking sequence alternation and ACKs.

    Decoupled from I/O to allow 100% unit-testability without async event loops.
    """

    def __init__(self, max_retries: int = 3, timeout_seconds: float = 2.0) -> None:
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.tx_seq: int = 0
        self.rx_seq: int | None = None
        self._pending_tx: OutboundTransaction | None = None

    def reset(self) -> None:
        """Reset sequence counters and clear pending transactions."""
        self.tx_seq = 0
        self.rx_seq = None
        self._pending_tx = None

    @property
    def has_pending_tx(self) -> bool:
        """Return True if an outbound command is currently awaiting ACK."""
        return self._pending_tx is not None

    @property
    def pending_tx(self) -> OutboundTransaction | None:
        """Return currently pending outbound transaction."""
        return self._pending_tx

    def prepare_outbound(
        self,
        payload: bytes,
        data_type: int = FrameDataType.DATA_MDR,
        start_marker: int = 0x3E,
        end_marker: int = 0x3C,
    ) -> tuple[Frame, bytes]:
        """Prepare an outbound frame using the current tx_seq.

        Returns:
            (Frame, encoded_bytes_ready_for_socket)
        """
        frame = Frame(data_type=data_type, seq=self.tx_seq, payload=payload)
        encoded = encode_frame(
            data_type=data_type,
            seq=self.tx_seq,
            payload=payload,
            start_marker=start_marker,
            end_marker=end_marker,
        )

        expected_ack = invert_seq(self.tx_seq)
        self._pending_tx = OutboundTransaction(
            frame=frame,
            encoded_bytes=encoded,
            expected_ack_seq=expected_ack,
            retries_left=self.max_retries,
        )
        return frame, encoded

    def handle_inbound_ack(self, ack_seq: int) -> bool:
        """Process an incoming ACK sequence number.

        Returns:
            True if this ACK satisfied the currently pending outbound transaction.
        """
        if self._pending_tx is None:
            return False

        if ack_seq == self._pending_tx.expected_ack_seq:
            self.tx_seq = invert_seq(self.tx_seq)
            if self._pending_tx.future and not self._pending_tx.future.done():
                self._pending_tx.future.set_result(None)
            self._pending_tx = None
            return True

        return False

    def handle_inbound_frame(
        self,
        frame: Frame,
        start_marker: int = 0x3E,
        end_marker: int = 0x3C,
    ) -> tuple[bytes | None, bool]:
        """Process any incoming frame.

        Returns:
            (ack_bytes_to_transmit_or_None, is_duplicate_frame)
        """
        # 1. Check if incoming frame is an ACK
        if frame.data_type == FrameDataType.ACK:
            self.handle_inbound_ack(frame.seq)
            return None, False

        # 2. Check for duplicate incoming data frame
        is_duplicate = (self.rx_seq is not None) and (frame.seq == self.rx_seq)
        self.rx_seq = frame.seq

        # 3. Check if response payload itself implicitly acknowledges our pending transaction
        if self._pending_tx is not None and frame.seq == self._pending_tx.expected_ack_seq:
            self.handle_inbound_ack(frame.seq)

        # 4. Generate ACK if required by this frame type
        ack_bytes: bytes | None = None
        if is_ack_required(frame.data_type):
            ack_seq = invert_seq(frame.seq)
            ack_bytes = encode_frame(
                data_type=FrameDataType.ACK,
                seq=ack_seq,
                payload=b"",
                start_marker=start_marker,
                end_marker=end_marker,
            )

        return ack_bytes, is_duplicate

    def prepare_retransmit(self) -> bytes:
        """Trigger retransmission of the pending outbound transaction.

        Returns:
            Raw bytes to resend.

        Raises:
            ARQTimeoutError: If max_retries has been exhausted.
            RuntimeError: If there is no pending transaction.
        """
        if self._pending_tx is None:
            raise RuntimeError("No pending transaction to retransmit")

        if self._pending_tx.retries_left <= 0:
            tx = self._pending_tx
            self._pending_tx = None
            if tx.future and not tx.future.done():
                tx.future.set_exception(
                    ARQTimeoutError(f"Command timed out after {self.max_retries} retries")
                )
            raise ARQTimeoutError(f"Command timed out after {self.max_retries} retries")

        self._pending_tx.retries_left -= 1
        return self._pending_tx.encoded_bytes


class AsyncARQController:
    """Asynchronous wrapper around ARQStateMachine for use in asyncio runtimes."""

    def __init__(
        self,
        send_fn: Callable[[bytes], asyncio.Future[None] | None] | None = None,
        max_retries: int = 3,
        timeout_seconds: float = 2.0,
    ) -> None:
        self.sm = ARQStateMachine(max_retries=max_retries, timeout_seconds=timeout_seconds)
        self._send_fn = send_fn
        self._lock = asyncio.Lock()

    def set_sender(self, send_fn: Callable[[bytes], asyncio.Future[None] | None]) -> None:
        """Configure callback to write bytes to socket."""
        self._send_fn = send_fn

    async def _send_raw(self, data: bytes) -> None:
        if self._send_fn is not None:
            res = self._send_fn(data)
            if asyncio.isfuture(res):
                await res

    async def send_command(
        self,
        payload: bytes,
        data_type: int = FrameDataType.DATA_MDR,
        start_marker: int = 0x3E,
        end_marker: int = 0x3C,
    ) -> None:
        """Transmit a command over ARQ, awaiting ACK with automatic retry."""
        async with self._lock:
            _frame, encoded = self.sm.prepare_outbound(
                payload, data_type=data_type, start_marker=start_marker, end_marker=end_marker
            )
            loop = asyncio.get_running_loop()
            fut: asyncio.Future[None] = loop.create_future()
            assert self.sm.pending_tx is not None
            self.sm.pending_tx.future = fut

            await self._send_raw(encoded)

            while not fut.done():
                try:
                    await asyncio.wait_for(asyncio.shield(fut), timeout=self.sm.timeout_seconds)
                except asyncio.TimeoutError:
                    if not self.sm.has_pending_tx:
                        break
                    try:
                        retry_bytes = self.sm.prepare_retransmit()
                        await self._send_raw(retry_bytes)
                    except ARQTimeoutError:
                        raise

    async def process_inbound(
        self,
        frame: Frame,
        start_marker: int = 0x3E,
        end_marker: int = 0x3C,
    ) -> tuple[Frame, bool]:
        """Process incoming frame, automatically transmitting ACK if required.

        Returns:
            (frame, is_duplicate)
        """
        ack_bytes, is_duplicate = self.sm.handle_inbound_frame(
            frame, start_marker=start_marker, end_marker=end_marker
        )
        if ack_bytes is not None:
            await self._send_raw(ack_bytes)
        return frame, is_duplicate
