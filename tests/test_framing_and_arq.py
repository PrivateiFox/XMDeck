"""Comprehensive unit tests for Sony MDR V2 framing, messages, and ARQ state machine."""

from __future__ import annotations

import asyncio

import pytest

from backend.protocol.arq import (
    ARQStateMachine,
    ARQTimeoutError,
    AsyncARQController,
    invert_seq,
    is_ack_required,
)
from backend.protocol.framing import (
    ALT_END_MARKER,
    ALT_START_MARKER,
    END_MARKER,
    START_MARKER,
    Frame,
    FramingError,
    StreamParser,
    calc_checksum,
    decode_frame,
    encode_frame,
    escape_bytes,
    unescape_bytes,
)
from backend.protocol.messages import (
    BatteryChargingStatus,
    CommandTable1,
    FrameDataType,
    NcAsmInquiredType,
    NcAsmMode,
    PowerInquiredType,
    build_battery_query,
    build_set_ambient_sound,
    build_set_anc_mode,
    build_set_speak_to_chat,
    build_speak_to_chat_query,
    parse_anc_state,
    parse_battery_status,
    parse_speak_to_chat,
)

# ===========================================================================
# 1. Byte Escaping & Unescaping Tests
# ===========================================================================


class TestEscaping:
    """Tests for pure Sony MDR byte escaping and unescaping."""

    def test_escape_plain_bytes_unchanged(self) -> None:
        raw = b"Hello, World! 12345\x00\xff"
        assert escape_bytes(raw) == raw
        assert unescape_bytes(raw) == raw

    def test_escape_individual_special_bytes(self) -> None:
        # 0x3C -> 0x3D 0x2C
        assert escape_bytes(b"\x3c") == b"\x3d\x2c"
        assert unescape_bytes(b"\x3d\x2c") == b"\x3c"

        # 0x3D -> 0x3D 0x2D
        assert escape_bytes(b"\x3d") == b"\x3d\x2d"
        assert unescape_bytes(b"\x3d\x2d") == b"\x3d"

        # 0x3E -> 0x3D 0x2E
        assert escape_bytes(b"\x3e") == b"\x3d\x2e"
        assert unescape_bytes(b"\x3d\x2e") == b"\x3e"

    def test_escape_adjacent_special_bytes(self) -> None:
        raw = bytes([0x3C, 0x3D, 0x3E, 0x3C])
        expected = bytes([0x3D, 0x2C, 0x3D, 0x2D, 0x3D, 0x2E, 0x3D, 0x2C])
        escaped = escape_bytes(raw)
        assert escaped == expected
        assert unescape_bytes(escaped) == raw

    def test_unescape_dangling_escape_sentry_raises(self) -> None:
        with pytest.raises(FramingError, match="Dangling escape byte"):
            unescape_bytes(b"data\x3d")

    def test_unescape_invalid_escaped_character_raises(self) -> None:
        # 0x00 is not a valid escaped byte (0x00 + 0x10 = 0x10, not in {0x3C, 0x3D, 0x3E})
        with pytest.raises(FramingError, match="Invalid escaped byte"):
            unescape_bytes(b"\x3d\x00")


# ===========================================================================
# 2. Checksum Tests
# ===========================================================================


class TestChecksum:
    """Tests for Sony MDR V2 additive checksum calculation."""

    def test_checksum_simple(self) -> None:
        assert calc_checksum(b"") == 0
        assert calc_checksum(b"\x01\x02\x03\x04") == 10
        assert calc_checksum(bytes([10, 20, 30])) == 60

    def test_checksum_overflow_wrap_around(self) -> None:
        # 250 + 10 = 260 -> 260 & 0xFF = 4
        assert calc_checksum(bytes([250, 10])) == 4
        assert calc_checksum(bytes([0xFF, 0x01])) == 0


# ===========================================================================
# 3. Frame Encoding & Decoding Tests
# ===========================================================================


class TestFraming:
    """Tests for packet serialization, framing delimiters, and parsing."""

    def test_encode_and_decode_round_trip_standard(self, sample_payload: bytes) -> None:
        encoded = encode_frame(
            data_type=FrameDataType.DATA_MDR,
            seq=0,
            payload=sample_payload,
            start_marker=START_MARKER,
            end_marker=END_MARKER,
        )
        assert encoded[0] == START_MARKER
        assert encoded[-1] == END_MARKER

        frame = decode_frame(encoded, start_marker=START_MARKER, end_marker=END_MARKER)
        assert frame.data_type == FrameDataType.DATA_MDR
        assert frame.seq == 0
        assert frame.payload == sample_payload

    def test_encode_and_decode_empty_payload(self) -> None:
        # e.g., ACK frame
        encoded = encode_frame(
            data_type=FrameDataType.ACK,
            seq=1,
            payload=b"",
            start_marker=START_MARKER,
            end_marker=END_MARKER,
        )
        frame = decode_frame(encoded)
        assert frame.data_type == FrameDataType.ACK
        assert frame.seq == 1
        assert frame.payload == b""

    def test_encode_and_decode_alternate_delimiters(self, sample_payload: bytes) -> None:
        encoded = encode_frame(
            data_type=FrameDataType.DATA_MDR,
            seq=1,
            payload=sample_payload,
            start_marker=ALT_START_MARKER,
            end_marker=ALT_END_MARKER,
        )
        assert encoded[0] == ALT_START_MARKER
        assert encoded[-1] == ALT_END_MARKER

        frame = decode_frame(encoded, start_marker=ALT_START_MARKER, end_marker=ALT_END_MARKER)
        assert frame.data_type == FrameDataType.DATA_MDR
        assert frame.seq == 1
        assert frame.payload == sample_payload

    def test_decode_truncated_packet_raises(self) -> None:
        with pytest.raises(FramingError, match="too short"):
            decode_frame(b"\x3e")

    def test_decode_invalid_delimiters_raises(self) -> None:
        valid = encode_frame(FrameDataType.ACK, 0, b"")
        # Corrupt start delimiter
        corrupt_start = bytes([0x00]) + valid[1:]
        with pytest.raises(FramingError, match="Invalid start delimiter"):
            decode_frame(corrupt_start)

        # Corrupt end delimiter
        corrupt_end = valid[:-1] + bytes([0x00])
        with pytest.raises(FramingError, match="Invalid end delimiter"):
            decode_frame(corrupt_end)

    def test_decode_corrupt_checksum_raises(self) -> None:
        encoded = encode_frame(FrameDataType.DATA_MDR, 0, b"Hello")
        # Modify a byte inside the escaped body
        corrupt = bytearray(encoded)
        corrupt[3] = (corrupt[3] + 1) & 0xFF
        with pytest.raises(FramingError):
            decode_frame(bytes(corrupt))


# ===========================================================================
# 4. StreamParser Tests
# ===========================================================================


class TestStreamParser:
    """Tests for stream reassembly across fragmented and back-to-back packets."""

    def test_single_complete_frame(self, valid_standard_frame: bytes) -> None:
        parser = StreamParser()
        frames = parser.feed(valid_standard_frame)
        assert len(frames) == 1
        assert frames[0].data_type == FrameDataType.DATA_MDR
        assert len(parser.buffer) == 0

    def test_fragmented_byte_by_byte(self, valid_standard_frame: bytes) -> None:
        parser = StreamParser()
        frames: list[Frame] = []
        for i in range(len(valid_standard_frame)):
            chunk = valid_standard_frame[i : i + 1]
            frames.extend(parser.feed(chunk))

        assert len(frames) == 1
        assert frames[0].data_type == FrameDataType.DATA_MDR
        assert len(parser.buffer) == 0

    def test_multiple_concatenated_frames(self) -> None:
        parser = StreamParser()
        f1 = encode_frame(FrameDataType.DATA_MDR, 0, b"Packet1")
        f2 = encode_frame(FrameDataType.ACK, 1, b"")
        f3 = encode_frame(FrameDataType.DATA_MDR, 1, b"Packet3")

        frames = parser.feed(f1 + f2 + f3)
        assert len(frames) == 3
        assert [f.payload for f in frames] == [b"Packet1", b"", b"Packet3"]
        assert [f.data_type for f in frames] == [
            FrameDataType.DATA_MDR,
            FrameDataType.ACK,
            FrameDataType.DATA_MDR,
        ]

    def test_noise_and_corruption_recovery(self, valid_standard_frame: bytes) -> None:
        parser = StreamParser()
        noise = b"\x00\x12\x34GarbageData\xff"
        corrupted_frame = b"\x3e\x12\x34\x3c"  # Bad frame

        frames = parser.feed(noise + corrupted_frame + noise + valid_standard_frame)
        assert len(frames) == 1
        assert frames[0].data_type == FrameDataType.DATA_MDR


# ===========================================================================
# 5. Message Serialization & Parsing Tests
# ===========================================================================


class TestMessages:
    """Tests for Sony MDR V2 battery, ANC, ambient, and speak-to-chat schemas."""

    def test_battery_query_and_response_single(self) -> None:
        query = build_battery_query(PowerInquiredType.BATTERY)
        assert query == bytes([CommandTable1.POWER_GET_STATUS, 0x00])

        # Normal 85%, charging
        resp = bytes(
            [
                CommandTable1.POWER_RET_STATUS,
                PowerInquiredType.BATTERY,
                85,
                BatteryChargingStatus.CHARGING,
            ]
        )
        status = parse_battery_status(resp)
        assert status.battery_level == 85
        assert status.charging is True
        assert status.left_level is None

        # 100%, not charging
        resp_charged = bytes(
            [
                CommandTable1.POWER_NTFY_STATUS,
                PowerInquiredType.BATTERY,
                100,
                BatteryChargingStatus.NOT_CHARGING,
            ]
        )
        status_charged = parse_battery_status(resp_charged)
        assert status_charged.battery_level == 100
        assert status_charged.charging is False

    def test_battery_response_dual_earbuds(self) -> None:
        # Left: 90% charging, Right: 80% not charging
        resp = bytes(
            [
                CommandTable1.POWER_RET_STATUS,
                PowerInquiredType.LEFT_RIGHT_BATTERY,
                90,
                BatteryChargingStatus.CHARGING,
                80,
                BatteryChargingStatus.NOT_CHARGING,
            ]
        )
        status = parse_battery_status(resp)
        assert status.left_level == 90
        assert status.left_charging is True
        assert status.right_level == 80
        assert status.right_charging is False
        assert status.battery_level == 85  # Average
        assert status.charging is True  # Either is charging

    def test_anc_mode_build_and_parse(self) -> None:
        # Cancelling mode
        cmd_nc = build_set_anc_mode("cancelling")
        assert cmd_nc[0] == CommandTable1.NCASM_SET_PARAM
        assert cmd_nc[3] == 0x01  # Total effect ON
        assert cmd_nc[4] == 0x00  # NC mode

        # Ambient mode, level 15, voice focus True
        cmd_amb = build_set_ambient_sound(level=15, voice_focus=True)
        assert cmd_amb[3] == 0x01  # Total effect ON
        assert cmd_amb[4] == 0x01  # ASM mode
        assert cmd_amb[5] == 0x01  # Focus on Voice
        assert cmd_amb[6] == 15  # Level 15

        # Off mode
        cmd_off = build_set_anc_mode("off")
        assert cmd_off[3] == 0x00  # Total effect OFF

        # Parse ANC notification
        ntfy = bytes(
            [
                CommandTable1.NCASM_NTFY_PARAM,
                NcAsmInquiredType.MODE_NC_ASM_DUAL_NC_MODE_SWITCH_AND_ASM_SEAMLESS,
                0x01,  # CHANGED
                0x01,  # Total effect ON
                NcAsmMode.ASM,
                0x01,  # VOICE
                12,  # Level
            ]
        )
        state = parse_anc_state(ntfy)
        assert state is not None
        assert state.mode == "ambient"
        assert state.ambient_level == 12
        assert state.voice_focus is True

        # Non-ANC packet returns None
        assert parse_anc_state(b"\x21\x00") is None

    def test_speak_to_chat_build_and_parse(self) -> None:
        query = build_speak_to_chat_query()
        assert query[0] == CommandTable1.SYSTEM_GET_PARAM

        # Enable STC
        cmd_enable = build_set_speak_to_chat(True)
        assert cmd_enable[0] == CommandTable1.SYSTEM_SET_PARAM
        assert cmd_enable[2] == 0x00  # ON

        # Disable STC
        cmd_disable = build_set_speak_to_chat(False)
        assert cmd_disable[2] == 0x01  # OFF

        # Parse STC status
        resp_on = bytes([CommandTable1.SYSTEM_RET_PARAM, 0x0C, 0x00, 0x01])
        assert parse_speak_to_chat(resp_on) is True

        resp_off = bytes([CommandTable1.SYSTEM_RET_PARAM, 0x0C, 0x01, 0x01])
        assert parse_speak_to_chat(resp_off) is False


# ===========================================================================
# 6. Stop-and-Wait ARQ State Machine Tests
# ===========================================================================


class TestARQStateMachine:
    """Tests for 1-bit sequence alternation, ACK matching, and retransmissions."""

    def test_invert_seq(self) -> None:
        assert invert_seq(0) == 1
        assert invert_seq(1) == 0

    def test_sequence_alternation_success_flow(self) -> None:
        arq = ARQStateMachine()
        assert arq.tx_seq == 0

        # Step 1: Prepare outbound frame (seq 0)
        frame1, _encoded1 = arq.prepare_outbound(b"Command1")
        assert frame1.seq == 0
        assert arq.has_pending_tx is True
        assert arq.pending_tx is not None
        assert arq.pending_tx.expected_ack_seq == 1

        # Step 2: Inbound ACK with seq 1 completes transaction
        ack_success = arq.handle_inbound_ack(1)
        assert ack_success is True
        assert arq.has_pending_tx is False
        assert arq.tx_seq == 1  # Alternated!

        # Step 3: Prepare next outbound frame (seq 1)
        frame2, _encoded2 = arq.prepare_outbound(b"Command2")
        assert frame2.seq == 1
        assert arq.pending_tx is not None
        assert arq.pending_tx.expected_ack_seq == 0

        # Wrong ACK (seq 1) ignored
        assert arq.handle_inbound_ack(1) is False
        assert arq.has_pending_tx is True

        # Correct ACK (seq 0) completes transaction
        assert arq.handle_inbound_ack(0) is True
        assert arq.has_pending_tx is False
        assert arq.tx_seq == 0  # Alternated back!

    def test_retransmission_and_timeout(self) -> None:
        arq = ARQStateMachine(max_retries=2)
        _frame, encoded = arq.prepare_outbound(b"Command")

        # Retry 1
        resend1 = arq.prepare_retransmit()
        assert resend1 == encoded
        assert arq.pending_tx is not None
        assert arq.pending_tx.retries_left == 1

        # Retry 2
        resend2 = arq.prepare_retransmit()
        assert resend2 == encoded
        assert arq.pending_tx is not None
        assert arq.pending_tx.retries_left == 0

        # Retry 3 -> Timeout error
        with pytest.raises(ARQTimeoutError, match="timed out"):
            arq.prepare_retransmit()

        assert arq.has_pending_tx is False

    def test_inbound_frame_ack_generation(self) -> None:
        arq = ARQStateMachine()

        # Inbound DATA_MDR with seq 0 -> Requires ACK with seq 1
        inbound = Frame(data_type=FrameDataType.DATA_MDR, seq=0, payload=b"Notification")
        ack_bytes, is_dup = arq.handle_inbound_frame(inbound)
        assert is_dup is False
        assert ack_bytes is not None

        ack_frame = decode_frame(ack_bytes)
        assert ack_frame.data_type == FrameDataType.ACK
        assert ack_frame.seq == 1
        assert ack_frame.payload == b""

        # Feeding identical frame -> Detected as duplicate
        ack_bytes2, is_dup2 = arq.handle_inbound_frame(inbound)
        assert is_dup2 is True
        assert ack_bytes2 is not None

    def test_inbound_shot_frame_no_ack_needed(self) -> None:
        arq = ARQStateMachine()
        assert not is_ack_required(FrameDataType.SHOT_MDR)

        inbound = Frame(data_type=FrameDataType.SHOT_MDR, seq=0, payload=b"Shot")
        ack_bytes, is_dup = arq.handle_inbound_frame(inbound)
        assert ack_bytes is None


# ===========================================================================
# 7. Async ARQ Controller Tests
# ===========================================================================


class TestAsyncARQController:
    """Async tests simulating socket interaction over ARQ."""

    def test_async_send_and_ack(self) -> None:
        async def run() -> None:
            sent_packets: list[bytes] = []

            def mock_socket_send(data: bytes) -> None:
                sent_packets.append(data)

            controller = AsyncARQController(send_fn=mock_socket_send, timeout_seconds=1.0)

            async def simulate_receiver() -> None:
                await asyncio.sleep(0.05)
                # Find the sent frame and simulate headphones acknowledging it
                raw = sent_packets[-1]
                frame = decode_frame(raw)
                # Send ACK back with 1 - seq
                ack_frame = Frame(
                    data_type=FrameDataType.ACK, seq=invert_seq(frame.seq), payload=b""
                )
                await controller.process_inbound(ack_frame)

            send_task = asyncio.create_task(controller.send_command(b"SetANC"))
            receiver_task = asyncio.create_task(simulate_receiver())

            await asyncio.gather(send_task, receiver_task)
            assert len(sent_packets) == 1
            assert controller.sm.has_pending_tx is False
            assert controller.sm.tx_seq == 1

        asyncio.run(run())
