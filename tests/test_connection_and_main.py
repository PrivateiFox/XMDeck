"""Unit tests for SonyConnection and Plugin RPC methods."""

from __future__ import annotations

import asyncio
from typing import Any

from backend.connection import SonyConnection
from backend.main import Plugin
from backend.protocol.framing import Frame
from backend.protocol.messages import (
    BatteryChargingStatus,
    CommandTable1,
    FrameDataType,
    NcAsmInquiredType,
    NcAsmMode,
    PowerInquiredType,
)


class TestSonyConnection:
    """Tests for SonyConnection state management and event dispatch."""

    def test_initial_state(self) -> None:
        conn = SonyConnection()
        assert conn.connected is False
        assert conn.is_busy is False
        assert conn.battery_status.battery_level is None
        assert conn.anc_state.mode == "cancelling"
        assert conn.speak_to_chat is False

    def test_state_notifications(self) -> None:
        conn = SonyConnection()
        events: list[tuple[str, Any]] = []

        conn.add_listener(lambda evt, data: events.append((evt, data)))

        # Simulate incoming battery frame
        battery_payload = bytes(
            [
                CommandTable1.POWER_NTFY_STATUS,
                PowerInquiredType.BATTERY,
                75,
                BatteryChargingStatus.CHARGING,
            ]
        )
        frame = Frame(data_type=FrameDataType.DATA_MDR, seq=0, payload=battery_payload)

        async def run() -> None:
            await conn._handle_incoming_frame(frame)

        asyncio.run(run())

        assert conn.battery_status.battery_level == 75
        assert conn.battery_status.charging is True
        assert len(events) >= 1
        assert events[0][0] == "battery_updated"
        assert events[0][1].battery_level == 75

    def test_anc_notification(self) -> None:
        conn = SonyConnection()
        events: list[tuple[str, Any]] = []
        conn.add_listener(lambda evt, data: events.append((evt, data)))

        anc_payload = bytes(
            [
                CommandTable1.NCASM_NTFY_PARAM,
                NcAsmInquiredType.MODE_NC_ASM_DUAL_NC_MODE_SWITCH_AND_ASM_SEAMLESS,
                0x01,  # CHANGED
                0x00,  # Total effect ON
                NcAsmMode.ASM,
                0x01,  # Focus on Voice
                14,  # Ambient level
            ]
        )
        frame = Frame(data_type=FrameDataType.DATA_MDR, seq=0, payload=anc_payload)

        async def run() -> None:
            await conn._handle_incoming_frame(frame)

        asyncio.run(run())

        assert conn.anc_state.mode == "ambient"
        assert conn.anc_state.ambient_level == 14
        assert conn.anc_state.voice_focus is True
        assert any(e[0] == "anc_updated" for e in events)


class TestPluginRPC:
    """Tests for Plugin class RPC endpoints."""

    def test_rpc_get_connection_status(self) -> None:
        plugin = Plugin()

        async def run() -> None:
            status = await plugin.get_connection_status()
            assert "connected" in status
            assert "device_name" in status
            assert "battery_level" in status
            assert "charging" in status
            assert "is_busy" in status
            assert status["connected"] is False

        asyncio.run(run())

    def test_rpc_get_anc_state(self) -> None:
        plugin = Plugin()

        async def run() -> None:
            state = await plugin.get_anc_state()
            assert "mode" in state
            assert "ambient_level" in state
            assert "voice_focus" in state
            assert state["mode"] in ("cancelling", "ambient", "off")

        asyncio.run(run())

    def test_plugin_lifecycle(self) -> None:
        plugin = Plugin()

        async def run() -> None:
            await plugin._main()
            assert plugin._running is True
            await plugin._unload()
            assert plugin._running is False

        asyncio.run(run())
