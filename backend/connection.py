"""Bluetooth RFCOMM connection management and BlueZ detection for Sony MDR headphones.

Handles:
- BlueZ device scanning and Sony MDR UUID detection
- Native Linux RFCOMM socket lifecycle (AF_BLUETOOTH, BTPROTO_RFCOMM)
- Stream parsing, ARQ handshakes, and background socket reader loop
- Thread-safe async state notification dispatch
"""

from __future__ import annotations

import asyncio
import logging
import re
import socket
import subprocess
from typing import Any, Callable

from .protocol.arq import AsyncARQController
from .protocol.framing import Frame, StreamParser
from .protocol.messages import (
    ANCState,
    BatteryStatus,
    build_anc_query,
    build_battery_query,
    build_set_ambient_sound,
    build_set_anc_mode,
    build_set_speak_to_chat,
    build_speak_to_chat_query,
    parse_anc_state,
    parse_battery_status,
    parse_speak_to_chat,
)

logger = logging.getLogger("xmdeck.connection")

# Standard Sony MDR Service UUID
SONY_MDR_UUID = "956C7B26-D49A-4BA8-B03F-B17D393CB6E2"
DEFAULT_RFCOMM_CHANNEL = 9

# Regex to validate Bluetooth MAC addresses (e.g. 00:11:22:33:44:55)
MAC_REGEX = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")


def is_rfcomm_supported() -> bool:
    """Check if native AF_BLUETOOTH RFCOMM sockets are supported in this Python runtime."""
    return hasattr(socket, "AF_BLUETOOTH") and hasattr(socket, "BTPROTO_RFCOMM")


def find_connected_sony_device() -> tuple[str | None, str | None]:
    """Scan connected Bluetooth devices via bluetoothctl for Sony WH/WF headphones.

    Returns:
        (mac_address, device_name) or (None, None) if not detected.
    """
    try:
        proc = subprocess.run(
            ["bluetoothctl", "devices", "Connected"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        if proc.returncode != 0:
            return None, None

        for line in proc.stdout.splitlines():
            # Line format: "Device AA:BB:CC:DD:EE:FF WH-1000XM4"
            parts = line.strip().split(maxsplit=2)
            if len(parts) >= 3 and parts[0] == "Device":
                mac = parts[1]
                name = parts[2]

                # Check name signature
                name_upper = name.upper()
                if any(x in name_upper for x in ("1000XM", "LINKBUDS", "ULT WEAR")):
                    return mac, name

                # Check device UUIDs via bluetoothctl info
                info_proc = subprocess.run(
                    ["bluetoothctl", "info", mac],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                    check=False,
                )
                if SONY_MDR_UUID.lower() in info_proc.stdout.lower():
                    return mac, name

    except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
        logger.debug("bluetoothctl device scan failed: %s", e)

    return None, None


class SonyConnection:
    """Manages an active RFCOMM socket to a Sony MDR headset."""

    def __init__(self) -> None:
        self.mac: str | None = None
        self.device_name: str | None = None
        self.connected: bool = False
        self.is_busy: bool = False

        self.battery_status = BatteryStatus(battery_level=None, charging=False)
        self.anc_state = ANCState(mode="cancelling", ambient_level=1, voice_focus=False)
        self.speak_to_chat: bool = False

        self._socket: socket.socket | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._parser = StreamParser()
        self._arq = AsyncARQController()
        self._arq.set_sender(self._raw_send)

        self._state_change_callbacks: list[Callable[[str, Any], None]] = []
        self._lock = asyncio.Lock()

    def add_listener(self, callback: Callable[[str, Any], None]) -> None:
        """Register a callback for state update notifications."""
        self._state_change_callbacks.append(callback)

    def _notify(self, event_type: str, data: Any) -> None:
        for cb in self._state_change_callbacks:
            try:
                cb(event_type, data)
            except Exception as e:
                logger.error("Error in state change callback: %s", e)

    def _raw_send(self, data: bytes) -> asyncio.Future[None]:
        """Write raw frame bytes to the non-blocking socket."""
        loop = asyncio.get_running_loop()
        fut = loop.create_future()

        if self._socket is None or not self.connected:
            fut.set_result(None)
            return fut

        try:
            self._socket.sendall(data)
            fut.set_result(None)
        except OSError as e:
            logger.error("Failed to write to RFCOMM socket: %s", e)
            fut.set_exception(e)
            asyncio.create_task(self.disconnect())

        return fut

    async def connect(
        self,
        mac: str,
        channel: int = DEFAULT_RFCOMM_CHANNEL,
        name: str | None = None,
    ) -> bool:
        """Establish RFCOMM socket connection to the specified Sony MAC address."""
        async with self._lock:
            if self.connected:
                return True

            if not is_rfcomm_supported():
                logger.warning(
                    "Native AF_BLUETOOTH is not supported on this platform. Connection unavailable."
                )
                self.is_busy = False
                return False

            self.mac = mac
            self.device_name = name or "Sony Headphones"
            self.is_busy = False

            try:
                loop = asyncio.get_running_loop()
                # Run blocking socket creation and connect in threadpool
                sock = await loop.run_in_executor(None, self._sync_connect, mac, channel)
                sock.setblocking(False)
                self._socket = sock
                self.connected = True
                self._parser.reset()
                self._arq.sm.reset()

                # Start background reader task
                self._reader_task = asyncio.create_task(self._socket_reader_loop())

                logger.info("Successfully connected to Sony MDR at %s (channel %d)", mac, channel)

                # Query initial states
                asyncio.create_task(self._query_initial_states())
                self._notify("connected", True)
                return True

            except OSError as e:
                logger.warning("Failed to connect to %s: %s", mac, e)
                # Check for EBUSY (channel locked by smartphone app)
                if getattr(e, "errno", None) in (16, 114):  # EBUSY or EALREADY
                    self.is_busy = True
                await self.disconnect()
                return False

    def _sync_connect(self, mac: str, channel: int) -> socket.socket:
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.settimeout(3.0)
        sock.connect((mac, channel))
        return sock

    async def disconnect(self) -> None:
        """Close RFCOMM socket connection and clean up reader task."""
        self.connected = False
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            self._reader_task = None

        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

        self._notify("connected", False)

    async def _socket_reader_loop(self) -> None:
        """Continuously read bytes from non-blocking RFCOMM socket into StreamParser."""
        loop = asyncio.get_running_loop()
        assert self._socket is not None

        try:
            while self.connected and self._socket:
                chunk = await loop.sock_recv(self._socket, 1024)
                if not chunk:
                    logger.info("RFCOMM socket closed by peer")
                    break

                frames = self._parser.feed(chunk)
                for frame in frames:
                    await self._handle_incoming_frame(frame)

        except asyncio.CancelledError:
            pass
        except OSError as e:
            logger.debug("Socket read error: %s", e)
        finally:
            await self.disconnect()

    async def _handle_incoming_frame(self, frame: Frame) -> None:
        """Process incoming Sony MDR frame and update state models."""
        processed_frame, is_duplicate = await self._arq.process_inbound(frame)
        if is_duplicate:
            return

        payload = processed_frame.payload
        if not payload:
            return

        # Check for Power Status (Battery)
        new_battery = parse_battery_status(payload)
        if new_battery.battery_level is not None:
            self.battery_status = new_battery
            self._notify("battery_updated", self.battery_status)

        # Check for ANC & Ambient Sound
        new_anc = parse_anc_state(payload)
        if new_anc.mode is not None:
            self.anc_state = new_anc
            self._notify("anc_updated", self.anc_state)

        # Check for Speak-to-Chat
        new_stc = parse_speak_to_chat(payload)
        self.speak_to_chat = new_stc
        self._notify("stc_updated", self.speak_to_chat)

    async def _query_initial_states(self) -> None:
        """Query initial battery, ANC, and Speak-to-Chat status after connecting."""
        try:
            await self.query_battery()
            await asyncio.sleep(0.1)
            await self.query_anc_state()
            await asyncio.sleep(0.1)
            await self.query_speak_to_chat()
        except Exception as e:
            logger.debug("Failed querying initial states: %s", e)

    async def query_battery(self) -> BatteryStatus:
        """Send battery status query over ARQ."""
        query = build_battery_query()
        await self._arq.send_command(query)
        return self.battery_status

    async def query_anc_state(self) -> ANCState:
        """Send ANC status query over ARQ."""
        query = build_anc_query()
        await self._arq.send_command(query)
        return self.anc_state

    async def query_speak_to_chat(self) -> bool:
        """Send Speak-to-Chat query over ARQ."""
        query = build_speak_to_chat_query()
        await self._arq.send_command(query)
        return self.speak_to_chat

    async def set_anc_mode(self, mode: str) -> bool:
        """Set ANC mode ('cancelling', 'ambient', or 'off')."""
        cmd = build_set_anc_mode(
            mode,
            ambient_level=self.anc_state.ambient_level,
            voice_focus=self.anc_state.voice_focus,
        )
        try:
            await self._arq.send_command(cmd)
            # Optimistically update local state
            valid_mode: Any = mode if mode in ("cancelling", "ambient", "off") else "cancelling"
            self.anc_state = ANCState(
                mode=valid_mode,
                ambient_level=self.anc_state.ambient_level,
                voice_focus=self.anc_state.voice_focus,
            )
            self._notify("anc_updated", self.anc_state)
            return True
        except Exception as e:
            logger.error("Failed to set ANC mode: %s", e)
            return False

    async def set_ambient_sound(self, level: int, voice_focus: bool) -> bool:
        """Set Ambient Sound level (1-20) and Voice Focus."""
        cmd = build_set_ambient_sound(level=level, voice_focus=voice_focus)
        try:
            await self._arq.send_command(cmd)
            # Optimistically update local state
            self.anc_state = ANCState(
                mode="ambient",
                ambient_level=max(1, min(20, level)),
                voice_focus=voice_focus,
            )
            self._notify("anc_updated", self.anc_state)
            return True
        except Exception as e:
            logger.error("Failed to set ambient sound: %s", e)
            return False

    async def set_speak_to_chat(self, enabled: bool) -> bool:
        """Enable or disable Speak-to-Chat."""
        cmd = build_set_speak_to_chat(enabled)
        try:
            await self._arq.send_command(cmd)
            self.speak_to_chat = enabled
            self._notify("stc_updated", self.speak_to_chat)
            return True
        except Exception as e:
            logger.error("Failed to set speak-to-chat: %s", e)
            return False
