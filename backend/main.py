"""Decky Loader Plugin entry point and JSON-RPC daemon for XMDeck."""

from __future__ import annotations

import asyncio
import contextlib
import re
import shutil
from typing import Any

from .connection import (
    SonyConnection,
    find_connected_sony_device,
    is_rfcomm_supported,
    quick_find_connected_sony_device,
    scan_all_bluetooth_devices,
)
from .logger import logger, setup_logging

try:
    import decky
except ImportError:
    try:
        import decky_plugin as decky  # type: ignore[import-not-found,no-redef]
    except ImportError:
        decky = None  # type: ignore[assignment]


class Plugin:
    """XMDeck Decky Loader Plugin class."""

    def __init__(self) -> None:
        setup_logging()
        self.conn = SonyConnection()
        self._monitor_task: asyncio.Task[None] | None = None
        self._fallback_task: asyncio.Task[None] | None = None
        self._monitor_proc: asyncio.subprocess.Process | None = None
        self._deactivate_task: asyncio.Task[None] | None = None
        self._inactivity_delay: float = 15.0
        self._running: bool = False
        self._ui_active: bool = False

    async def _main(self) -> None:
        """Decky plugin entry point: initializes event listeners."""
        self._running = True
        logger.info("XMDeck plugin starting...")

        # Hook state updates to emit events to frontend
        self.conn.add_listener(self._on_state_updated)

        # Connection is established on-demand when user opens the plugin UI tab

    async def _unload(self) -> None:
        """Decky plugin teardown."""
        self._running = False
        self._ui_active = False
        logger.info("XMDeck plugin unloading...")

        if self._deactivate_task and not self._deactivate_task.done():
            self._deactivate_task.cancel()
            self._deactivate_task = None

        await self._stop_bluetooth_monitor()
        await self.conn.disconnect()

    def _on_state_updated(self, event_type: str, data: Any) -> None:
        """Dispatch real-time updates to Decky frontend when state changes."""
        if decky is not None and hasattr(decky, "emit"):
            asyncio.create_task(
                decky.emit(
                    "xmdeck_state_changed",
                    {
                        "event": event_type,
                        "connection": self._build_connection_status_dict(),
                        "anc": self._build_anc_dict(),
                        "speak_to_chat": self.conn.speak_to_chat,
                    },
                )
            )

    async def _delayed_deactivate(self) -> None:
        """Grace period before tearing down RFCOMM, preventing churn during UI interactions."""
        try:
            logger.debug("UI unfocused: grace period started (%ss)...", self._inactivity_delay)
            await asyncio.sleep(self._inactivity_delay)
            self._ui_active = False
            logger.info("UI grace period expired: releasing RFCOMM connection")
            await self._stop_bluetooth_monitor()
            if self.conn.connected:
                await self.conn.disconnect()
        except asyncio.CancelledError:
            logger.debug("UI grace period cancelled (user returned to XMDeck)")

    async def set_ui_active(self, active: bool) -> bool:
        """Handle UI tab visibility changes with debouncing to prevent socket churn."""
        logger.info("set_ui_active called: %s (current: %s)", active, self._ui_active)

        if active:
            # Cancel any pending deactivation countdown
            if self._deactivate_task and not self._deactivate_task.done():
                logger.info("Cancelling pending UI deactivation timer")
                self._deactivate_task.cancel()
                self._deactivate_task = None

            self._ui_active = True
            # Tab opened: start reactive event monitor if not already running
            if self._monitor_task is None or self._monitor_task.done():
                self._monitor_task = asyncio.create_task(self._start_bluetooth_monitor())
        else:
            # Component unmounted (dropdown opened or tab switched)
            # Start grace period timer instead of immediately disconnecting
            if self._deactivate_task is None or self._deactivate_task.done():
                self._deactivate_task = asyncio.create_task(self._delayed_deactivate())

        return True

    async def _stop_bluetooth_monitor(self) -> None:
        """Clean up background monitor process, fallback loop, and reader task."""
        if self._fallback_task:
            if not self._fallback_task.done():
                self._fallback_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._fallback_task
            self._fallback_task = None

        if self._monitor_task:
            if not self._monitor_task.done():
                self._monitor_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._monitor_task
            self._monitor_task = None

        if self._monitor_proc:
            with contextlib.suppress(Exception):
                self._monitor_proc.terminate()
                await self._monitor_proc.wait()
            self._monitor_proc = None

    async def _fallback_loop(self) -> None:
        """Lightweight safety fallback ping while UI is open and headphones are disconnected."""
        while self._running and self._ui_active:
            try:
                # Sleep 5 seconds between fast safety checks
                await asyncio.sleep(5.0)

                if self._ui_active and not self.conn.connected:
                    logger.debug("Running lightweight safety check for connected Sony device...")
                    await self.trigger_connect()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Error in safety fallback loop: %s", e)

    async def _start_bluetooth_monitor(self) -> None:
        """Stream BlueZ events reactively with dbus-monitor and a lightweight safety fallback."""
        # Initial fast check in case headphones are already connected
        if not self.conn.connected and self._ui_active:
            await self.trigger_connect()

        # Launch safety fallback loop
        if self._fallback_task is None or self._fallback_task.done():
            self._fallback_task = asyncio.create_task(self._fallback_loop())

        # Determine monitor command
        cmd: list[str] | None = None
        if shutil.which("dbus-monitor"):
            cmd = [
                "dbus-monitor",
                "--system",
                (
                    "type='signal',sender='org.bluez',"
                    "interface='org.freedesktop.DBus.Properties',"
                    "member='PropertiesChanged'"
                ),
            ]
        elif shutil.which("bluetoothctl"):
            cmd = ["bluetoothctl"]

        if not cmd:
            logger.debug("No streaming monitor CLI available, relying on safety loop")
            return

        # Stream real-time events while tab is open
        while self._running and self._ui_active:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                self._monitor_proc = proc

                assert proc.stdout is not None
                current_mac: str | None = None
                current_prop: str | None = None

                while self._running and self._ui_active:
                    line_bytes = await proc.stdout.readline()
                    if not line_bytes:
                        break  # EOF / monitor exited

                    line = line_bytes.decode("utf-8", errors="replace").strip()

                    # Reset property tracker on new signal header
                    if line.startswith("signal "):
                        current_prop = None
                        path_match = re.search(r"dev_([0-9A-Fa-f]{2}_){5}[0-9A-Fa-f]{2}", line)
                        if path_match:
                            current_mac = path_match.group(0)[4:].replace("_", ":")

                    # Also match standard MAC format: AA:BB:CC:DD:EE:FF
                    mac_match = re.search(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", line)
                    if mac_match:
                        current_mac = mac_match.group(0)

                    # Track current property key in multiline D-Bus output
                    if 'string "Connected"' in line:
                        current_prop = "Connected"
                    elif 'string "ServicesResolved"' in line:
                        current_prop = "ServicesResolved"
                    elif line.startswith('string "') or line.startswith("dict entry"):
                        current_prop = None

                    # Connection signal
                    is_connect = (
                        "Connected: yes" in line
                        or (
                            current_prop in ("Connected", "ServicesResolved")
                            and "boolean true" in line
                        )
                    )
                    if is_connect and current_mac and not self.conn.connected and self._ui_active:
                        logger.info(
                            "Reactive BlueZ connect signal: %s. Checking...",
                            current_mac,
                        )
                        await self.trigger_connect(target_mac=current_mac)

                    # Disconnection signal
                    is_disconnect = (
                        "Connected: no" in line
                        or (current_prop == "Connected" and "boolean false" in line)
                    )
                    if is_disconnect and current_mac and self.conn.connected:
                        if self.conn.mac and current_mac.lower() == self.conn.mac.lower():
                            logger.info(
                                "Reactive BlueZ disconnect signal: %s",
                                current_mac,
                            )
                            await self.conn.disconnect()

            except (FileNotFoundError, OSError) as e:
                logger.debug("Streaming monitor unavailable: %s", e)
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in streaming monitor: %s", e)
                await asyncio.sleep(2.0)
            finally:
                if self._monitor_proc:
                    with contextlib.suppress(Exception):
                        self._monitor_proc.terminate()
                        await self._monitor_proc.wait()
                    self._monitor_proc = None

            if self._running and self._ui_active:
                await asyncio.sleep(2.0)

    # -----------------------------------------------------------------------
    # JSON-RPC Methods exposed to Frontend
    # -----------------------------------------------------------------------

    def _build_connection_status_dict(self) -> dict[str, Any]:
        return {
            "connected": self.conn.connected,
            "device_name": self.conn.device_name if self.conn.connected else None,
            "mac": self.conn.mac,
            "battery_level": self.conn.battery_status.battery_level,
            "charging": self.conn.battery_status.charging,
            "is_busy": self.conn.is_busy,
            "last_error": self.conn.last_error,
            "channel": self.conn.channel,
        }

    def _build_anc_dict(self) -> dict[str, Any]:
        return {
            "mode": self.conn.anc_state.mode,
            "ambient_level": self.conn.anc_state.ambient_level,
            "voice_focus": self.conn.anc_state.voice_focus,
        }

    async def get_connection_status(self) -> dict[str, Any]:
        """Return current Bluetooth connection and battery status."""
        return self._build_connection_status_dict()

    async def get_anc_state(self) -> dict[str, Any]:
        """Return current Active Noise Cancellation & Ambient Sound state."""
        return self._build_anc_dict()

    async def set_anc_mode(self, mode: str) -> bool:
        """Switch ANC mode: 'cancelling', 'ambient', or 'off'."""
        return await self.conn.set_anc_mode(mode)

    async def set_ambient_sound(self, level: int, voice_focus: bool) -> bool:
        """Adjust Ambient Sound level (1-20) and Voice Focus."""
        return await self.conn.set_ambient_sound(level, voice_focus)

    async def set_speak_to_chat(self, enabled: bool) -> bool:
        """Enable or disable Speak-to-Chat."""
        return await self.conn.set_speak_to_chat(enabled)

    async def connect_device(
        self, mac: str, name: str | None = None, channel: int | None = None
    ) -> bool:
        """Manually trigger connection to a specific Bluetooth MAC."""
        logger.info("Manual connection requested to MAC: %s (channel: %s)", mac, channel)
        return await self.conn.connect(mac, channel=channel, name=name)

    async def disconnect_device(self) -> bool:
        """Manually disconnect active RFCOMM connection."""
        logger.info("Manual disconnect requested")
        await self.conn.disconnect()
        return True

    async def trigger_connect(self, target_mac: str | None = None) -> dict[str, Any]:
        """Trigger an immediate connection attempt to Sony headphones."""
        logger.debug("trigger_connect invoked (target_mac=%s)", target_mac)
        loop = asyncio.get_running_loop()

        # Try fast 10ms check first
        mac, name = await loop.run_in_executor(None, quick_find_connected_sony_device)

        # Fallback to full device scan if quick check didn't locate candidate
        if not mac:
            mac, name = await loop.run_in_executor(None, find_connected_sony_device)

        if not mac and target_mac:
            devs = await loop.run_in_executor(None, scan_all_bluetooth_devices)
            for d in devs:
                is_match = d["mac"].lower() == target_mac.lower()
                if is_match and d.get("is_sony") and not d.get("is_le"):
                    mac = d["mac"]
                    name = d.get("name")
                    break

        if mac and (self._ui_active or self.conn.connected):
            logger.info("trigger_connect: Found Sony device %s (%s). Connecting...", name, mac)
            await self.conn.connect(mac, name=name)
        else:
            if not self.conn.connected:
                self.conn.last_error = "No Sony headphones found in Bluetooth scan"

        return self._build_connection_status_dict()

    async def scan_devices(self) -> list[dict[str, Any]]:
        """Scan and return all Bluetooth devices found on the system."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, scan_all_bluetooth_devices)

    async def get_diagnostics(self) -> dict[str, Any]:
        """Return full Bluetooth diagnostics and detected devices for UI troubleshooting."""
        loop = asyncio.get_running_loop()
        devices = await loop.run_in_executor(None, scan_all_bluetooth_devices)
        return {
            "connected": self.conn.connected,
            "mac": self.conn.mac,
            "device_name": self.conn.device_name,
            "rfcomm_supported": is_rfcomm_supported(),
            "last_error": self.conn.last_error,
            "channel": self.conn.channel,
            "devices": devices,
        }
