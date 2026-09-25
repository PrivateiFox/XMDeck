"""Unit tests for SonyConnection and Plugin RPC methods."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

from backend.connection import (
    SonyConnection,
    find_connected_sony_device,
    find_rfcomm_channel,
    quick_find_connected_sony_device,
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

    @patch("subprocess.run")
    def test_quick_find_connected_sony_device(self, mock_run: MagicMock) -> None:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = (
            "Device 11:22:33:44:55:66 Xbox Wireless Controller\n"
            "Device AA:BB:CC:DD:EE:FF WH-1000XM5\n"
        )
        mac, name = quick_find_connected_sony_device()
        assert mac == "AA:BB:CC:DD:EE:FF"
        assert name == "WH-1000XM5"


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
        plugin._inactivity_delay = 0.01

        async def run() -> None:
            await plugin._main()
            assert plugin._running is True
            assert plugin._ui_active is False
            assert plugin._monitor_task is None

            # Test activating UI
            with patch.object(plugin, "trigger_connect") as mock_trigger:
                mock_trigger.return_value = {}
                await plugin.set_ui_active(True)
                assert plugin._ui_active is True
                assert plugin._monitor_task is not None

                # Test deactivating UI with debounced grace period
                await plugin.set_ui_active(False)
                assert plugin._deactivate_task is not None
                await plugin._deactivate_task
                assert plugin._ui_active is False
                assert plugin._monitor_task is None

            await plugin._unload()
            assert plugin._running is False

        asyncio.run(run())

    def test_set_ui_active_cancels_when_reopened(self) -> None:
        plugin = Plugin()
        plugin._inactivity_delay = 1.0

        async def run() -> None:
            await plugin._main()
            with patch.object(plugin, "trigger_connect"):
                await plugin.set_ui_active(True)
                assert plugin._ui_active is True
                # User opens dropdown (unmounts)
                await plugin.set_ui_active(False)
                assert plugin._deactivate_task is not None
                # User selects item (remounts quickly)
                await plugin.set_ui_active(True)
                assert plugin._deactivate_task is None
                assert plugin._ui_active is True
            await plugin._unload()

        asyncio.run(run())

    def test_set_ui_active_disconnects_socket_after_grace_period(self) -> None:
        plugin = Plugin()
        plugin._inactivity_delay = 0.01

        async def run() -> None:
            await plugin._main()
            plugin.conn.connected = True
            with patch.object(plugin.conn, "disconnect") as mock_disconnect:
                mock_disconnect.return_value = None
                await plugin.set_ui_active(False)
                await asyncio.sleep(0.02)
                mock_disconnect.assert_called_once()
            await plugin._unload()

        asyncio.run(run())

    def test_reactive_bluetooth_events(self) -> None:
        plugin = Plugin()

        async def run() -> None:
            await plugin._main()

            mock_proc = MagicMock()
            simulated_lines = [
                b"[CHG] Device AA:BB:CC:DD:EE:FF Connected: yes\n",
                b"[CHG] Device AA:BB:CC:DD:EE:FF Connected: no\n",
                b"",
            ]

            async def readline() -> bytes:
                if simulated_lines:
                    return simulated_lines.pop(0)
                await asyncio.sleep(3600)
                return b""

            mock_proc.stdout.readline = readline
            mock_proc.terminate = MagicMock()

            async def wait() -> int:
                return 0

            mock_proc.wait = wait

            with patch("shutil.which", return_value="/usr/bin/dbus-monitor"), \
                 patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
                 patch.object(plugin, "trigger_connect") as mock_connect, \
                 patch.object(plugin.conn, "disconnect") as mock_disconnect:

                async def connect_side_effect(target_mac: str | None = None) -> dict[str, Any]:
                    plugin.conn.connected = True
                    plugin.conn.mac = target_mac or "AA:BB:CC:DD:EE:FF"
                    return {}

                mock_connect.side_effect = connect_side_effect
                mock_disconnect.return_value = None
                plugin.conn.connected = False

                await plugin.set_ui_active(True)
                await asyncio.sleep(0.05)

                assert mock_connect.called
                assert mock_disconnect.called

                await plugin.set_ui_active(False)

            await plugin._unload()

        asyncio.run(run())

    def test_reactive_dbus_monitor_format(self) -> None:
        plugin = Plugin()

        async def run() -> None:
            await plugin._main()

            mock_proc = MagicMock()
            sig_header = (
                b"signal path=/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF; "
                b"interface=org.freedesktop.DBus.Properties; member=PropertiesChanged\n"
            )
            simulated_lines = [
                sig_header,
                b'   string "Connected"\n',
                b"   variant boolean true\n",
                sig_header,
                b'   string "Connected"\n',
                b"   variant boolean false\n",
                b"",
            ]

            async def readline() -> bytes:
                if simulated_lines:
                    return simulated_lines.pop(0)
                await asyncio.sleep(3600)
                return b""

            mock_proc.stdout.readline = readline
            mock_proc.terminate = MagicMock()

            async def wait() -> int:
                return 0

            mock_proc.wait = wait

            with patch("shutil.which", return_value="/usr/bin/dbus-monitor"), \
                 patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
                 patch.object(plugin, "trigger_connect") as mock_connect, \
                 patch.object(plugin.conn, "disconnect") as mock_disconnect:

                async def connect_side_effect(target_mac: str | None = None) -> dict[str, Any]:
                    plugin.conn.connected = True
                    plugin.conn.mac = target_mac or "AA:BB:CC:DD:EE:FF"
                    return {}

                mock_connect.side_effect = connect_side_effect
                mock_disconnect.return_value = None
                plugin.conn.connected = False

                await plugin.set_ui_active(True)
                await asyncio.sleep(0.05)

                assert mock_connect.called
                assert mock_disconnect.called

                await plugin.set_ui_active(False)

            await plugin._unload()

        asyncio.run(run())


class TestLogging:
    """Tests for logging configuration and verbosity settings."""

    def test_default_log_level_is_info(self) -> None:
        import logging
        import os

        from backend.logger import _get_log_level

        with patch.dict(os.environ, {}, clear=True):
            assert _get_log_level() == logging.INFO

    def test_log_level_env_override(self) -> None:
        import logging
        import os

        from backend.logger import _get_log_level

        with patch.dict(os.environ, {"XMDECK_LOG_LEVEL": "WARNING"}):
            assert _get_log_level() == logging.WARNING

    def test_debug_flag_env_override(self) -> None:
        import logging
        import os

        from backend.logger import _get_log_level

        with patch.dict(os.environ, {"XMDECK_DEBUG": "1"}):
            assert _get_log_level() == logging.DEBUG
        with patch.dict(os.environ, {"XMDECK_DEBUG": "true"}):
            assert _get_log_level() == logging.DEBUG
