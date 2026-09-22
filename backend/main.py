"""Decky Loader Plugin entry point and JSON-RPC daemon for XMDeck."""

from __future__ import annotations

import asyncio
from typing import Any

from .connection import (
    SonyConnection,
    find_connected_sony_device,
    is_rfcomm_supported,
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
        self._poll_task: asyncio.Task[None] | None = None
        self._running: bool = False

    async def _main(self) -> None:
        """Decky plugin entry point: initializes device discovery and event listeners."""
        self._running = True
        logger.info("XMDeck plugin starting...")

        # Hook state updates to emit events to frontend
        self.conn.add_listener(self._on_state_updated)

        # Launch auto-discovery loop
        self._poll_task = asyncio.create_task(self._auto_discovery_loop())

    async def _unload(self) -> None:
        """Decky plugin teardown."""
        self._running = False
        logger.info("XMDeck plugin unloading...")

        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            self._poll_task = None

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

    async def _auto_discovery_loop(self) -> None:
        """Periodically scan for connected Sony headphones and establish RFCOMM link."""
        while self._running:
            try:
                if not self.conn.connected:
                    mac, name = await asyncio.get_running_loop().run_in_executor(
                        None, find_connected_sony_device
                    )
                    if mac:
                        logger.info(
                            "Found candidate Sony device: %s (%s). Attempting connect...",
                            name,
                            mac,
                        )
                        connected = await self.conn.connect(mac, name=name)
                        if connected:
                            logger.info(
                                "Connected successfully to %s on channel %s",
                                mac,
                                self.conn.channel,
                            )
                        else:
                            logger.warning("Failed to connect to %s: %s", mac, self.conn.last_error)

                # Wait before next poll interval: 5s if connected, 4s if trying to connect
                await asyncio.sleep(5.0 if self.conn.connected else 4.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in auto-discovery loop: %s", e)
                await asyncio.sleep(4.0)

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
