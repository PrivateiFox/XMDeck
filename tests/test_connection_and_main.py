"""Unit tests for SonyConnection and Plugin RPC methods."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

from backend.connection import (
    SonyConnection,
    find_connected_sony_device,
    find_rfcomm_channel,
)
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
                0x01,  # Total effect ON
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


class TestDeviceDiscovery:
    """Tests for Bluetooth device discovery and prioritization."""

    @patch("subprocess.run")
    def test_classic_preferred_over_le(self, mock_run: MagicMock) -> None:
        # Mock bluetoothctl devices Connected returning both LE and Classic
        mock_devices_output = (
            "Device 11:22:33:44:55:66 LE_WH-1000XM6\nDevice AA:BB:CC:DD:EE:FF WH-1000XM6\n"
        )
        mock_info_classic = (
            "Device AA:BB:CC:DD:EE:FF (public)\n"
            "Name: WH-1000XM6\n"
            "Alias: WH-1000XM6\n"
            "Connected: yes\n"
            "UUID: Vendor specific (956c7b26-d49a-4ba8-b03f-b17d393cb6e2)\n"
        )
        mock_info_le = (
            "Device 11:22:33:44:55:66 (random)\n"
            "Name: LE_WH-1000XM6\n"
            "Alias: LE_WH-1000XM6\n"
            "Connected: yes\n"
        )

        def side_effect(cmd: list[str], **kwargs: Any) -> MagicMock:
            res = MagicMock()
            res.returncode = 0
            if "Connected" in cmd:
                res.stdout = mock_devices_output
            elif "AA:BB:CC:DD:EE:FF" in cmd:
                res.stdout = mock_info_classic
            elif "11:22:33:44:55:66" in cmd:
                res.stdout = mock_info_le
            else:
                res.stdout = ""
            return res

        mock_run.side_effect = side_effect

        mac, name = find_connected_sony_device()
        # Must pick Classic Bluetooth MAC AA:BB:CC:DD:EE:FF instead of LE 11:22:33:44:55:66!
        assert mac == "AA:BB:CC:DD:EE:FF"
        assert name == "WH-1000XM6"

    @patch("subprocess.run")
    def test_find_rfcomm_channel_parsing(self, mock_run: MagicMock) -> None:
        mock_sdp_out = (
            "Service Name: Sony MDR-V2 Service\n"
            "Service Description: Sony Wireless Noise Canceling\n"
            "Service Class ID List:\n"
            "  UUID 128: 956c7b26-d49a-4ba8-b03f-b17d393cb6e2\n"
            "Protocol Descriptor List:\n"
            '  "L2CAP" (0x0100)\n'
            '  "RFCOMM" (0x0003)\n'
            "    Channel: 8\n"
        )
        res = MagicMock()
        res.returncode = 0
        res.stdout = mock_sdp_out
        mock_run.return_value = res

        ch = find_rfcomm_channel("AA:BB:CC:DD:EE:FF")
        assert ch == 8


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
            assert "mac" in status
            assert "last_error" in status
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

    @patch("backend.main.scan_all_bluetooth_devices")
    def test_rpc_diagnostics(self, mock_scan: MagicMock) -> None:
        mock_scan.return_value = [
            {
                "mac": "AA:BB:CC:DD:EE:FF",
                "name": "WH-1000XM6",
                "alias": "WH-1000XM6",
                "connected": True,
                "uuids": ["956c7b26-d49a-4ba8-b03f-b17d393cb6e2"],
                "icon": "audio-headphones",
                "is_sony": True,
                "is_le": False,
            }
        ]
        plugin = Plugin()

        async def run() -> None:
            diag = await plugin.get_diagnostics()
            assert "connected" in diag
            assert "devices" in diag
            assert len(diag["devices"]) == 1
            assert diag["devices"][0]["name"] == "WH-1000XM6"
            assert diag["devices"][0]["is_sony"] is True

        asyncio.run(run())

    def test_plugin_lifecycle(self) -> None:
        plugin = Plugin()

        async def run() -> None:
            await plugin._main()
            assert plugin._running is True
            await plugin._unload()
            assert plugin._running is False

        asyncio.run(run())
