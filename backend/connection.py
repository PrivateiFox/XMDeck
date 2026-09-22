"""Bluetooth RFCOMM connection management and BlueZ detection for Sony MDR headphones.

Handles:
- BlueZ device scanning and Sony MDR UUID detection across Classic BT and BLE
- Native Linux RFCOMM socket lifecycle (AF_BLUETOOTH, BTPROTO_RFCOMM)
- Dynamic SDP channel resolution and candidate channel fallback
- Stream parsing, ARQ handshakes, and background socket reader loop
- Thread-safe async state notification dispatch
"""

from __future__ import annotations

import asyncio
import json
import re
import socket
import subprocess
from typing import Any, Callable

from .logger import logger
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

# Standard Sony MDR Service UUIDs
SONY_MDR_UUID_V2 = "956c7b26-d49a-4ba8-b03f-b17d393cb6e2"
SONY_MDR_UUID_V2_ALT = "956c7b26-b496-4447-ad7b-3a47900d8c86"
SONY_MDR_UUID_V1 = "96cc203e-5068-46ad-b32d-e316f5e069ba"
SONY_MDR_UUID_V1_ALT = "96cc203e-50f8-4944-9c22-edcb48f6216f"
SONY_FAST_PAIR_UUID = "df21fe2c-2515-4fdb-8886-f12c4d67927c"

SONY_UUIDS = (
    SONY_MDR_UUID_V2,
    SONY_MDR_UUID_V2_ALT,
    SONY_MDR_UUID_V1,
    SONY_MDR_UUID_V1_ALT,
    SONY_FAST_PAIR_UUID,
)

# Model identifiers and signatures
SONY_NAME_KEYWORDS = (
    "1000X",
    "WH-",
    "WF-",
    "SONY",
    "LINKBUDS",
    "ULT WEAR",
    "MDR-",
    "CH7",
    "CH5",
    "C700",
    "C500",
)

DEFAULT_RFCOMM_CHANNEL = 9
FALLBACK_RFCOMM_CHANNELS = (9, 8, 1, 2, 3, 5, 7, 10, 11)

# Regex to validate Bluetooth MAC addresses (e.g. 00:11:22:33:44:55)
MAC_REGEX = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")


def is_rfcomm_supported() -> bool:
    """Check if native AF_BLUETOOTH RFCOMM sockets are supported in this Python runtime."""
    return hasattr(socket, "AF_BLUETOOTH") and hasattr(socket, "BTPROTO_RFCOMM")


def scan_all_bluetooth_devices() -> list[dict[str, Any]]:
    """Scan all paired and connected Bluetooth devices from BlueZ via bluetoothctl & busctl.

    Returns:
        List of device records:
        [
            {
                "mac": str,
                "name": str,
                "alias": str,
                "connected": bool,
                "uuids": list[str],
                "icon": str,
                "is_sony": bool,
                "is_le": bool,
            },
            ...
        ]
    """
    devices_dict: dict[str, dict[str, Any]] = {}

    # Method 1: Scan via bluetoothctl (devices Connected, devices Paired, devices)
    for subcmd in (["devices", "Connected"], ["devices", "Paired"], ["devices"]):
        try:
            proc = subprocess.run(
                ["bluetoothctl", *subcmd],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout:
                for line in proc.stdout.splitlines():
                    parts = line.strip().split(maxsplit=2)
                    if len(parts) >= 2 and parts[0] == "Device":
                        mac = parts[1]
                        if MAC_REGEX.match(mac):
                            name = parts[2] if len(parts) >= 3 else mac
                            if mac not in devices_dict:
                                devices_dict[mac] = {
                                    "mac": mac,
                                    "name": name,
                                    "alias": name,
                                    "connected": "Connected" in subcmd,
                                    "uuids": [],
                                    "icon": "",
                                    "is_sony": False,
                                    "is_le": False,
                                }
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
            logger.debug("bluetoothctl %s failed: %s", " ".join(subcmd), e)

    # Method 2: Query D-Bus directly via busctl if available (fast & comprehensive)
    try:
        busctl_proc = subprocess.run(
            [
                "busctl",
                "call",
                "org.bluez",
                "/",
                "org.freedesktop.DBus.ObjectManager",
                "GetManagedObjects",
                "--json=pretty",
            ],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        if busctl_proc.returncode == 0 and busctl_proc.stdout:
            data = json.loads(busctl_proc.stdout)
            # data has structure: {"data": [ {path: {interface: {prop: {data: ...}}}} ] }
            objects = data.get("data", [{}])[0]
            for _obj_path, ifaces in objects.items():
                if "org.bluez.Device1" in ifaces:
                    dev = ifaces["org.bluez.Device1"]
                    addr = dev.get("Address", {}).get("data", "")
                    if MAC_REGEX.match(addr):
                        dev_name = dev.get("Name", {}).get("data", addr)
                        dev_alias = dev.get("Alias", {}).get("data", dev_name)
                        is_conn = bool(dev.get("Connected", {}).get("data", False))
                        uuids_raw = dev.get("UUIDs", {}).get("data", [])
                        uuids = [str(u).lower() for u in uuids_raw]
                        icon = dev.get("Icon", {}).get("data", "")

                        devices_dict[addr] = {
                            "mac": addr,
                            "name": dev_name,
                            "alias": dev_alias,
                            "connected": is_conn,
                            "uuids": uuids,
                            "icon": icon,
                            "is_sony": False,
                            "is_le": False,
                        }
    except Exception as e:
        logger.debug("busctl BlueZ scan skipped: %s", e)

    # Method 3: Enrich devices with bluetoothctl info
    results: list[dict[str, Any]] = []
    for mac, dev in devices_dict.items():
        if not dev["uuids"] or not dev["connected"]:
            try:
                info_proc = subprocess.run(
                    ["bluetoothctl", "info", mac],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                    check=False,
                )
                if info_proc.returncode == 0 and info_proc.stdout:
                    info_out = info_proc.stdout
                    dev["connected"] = "Connected: yes" in info_out

                    for line in info_out.splitlines():
                        line_s = line.strip()
                        if line_s.startswith("Name:"):
                            dev["name"] = line_s.split("Name:", 1)[1].strip()
                        elif line_s.startswith("Alias:"):
                            dev["alias"] = line_s.split("Alias:", 1)[1].strip()
                        elif line_s.startswith("Icon:"):
                            dev["icon"] = line_s.split("Icon:", 1)[1].strip()
                        elif "UUID:" in line_s:
                            # Extract UUID if present (e.g. "UUID: Vendor specific (956c...)")
                            m = re.search(r"\(([0-9a-fA-F-]{36})\)", line_s)
                            if m:
                                dev["uuids"].append(m.group(1).lower())
                        elif "Battery Percentage:" in line_s:
                            m_bat = re.search(r"\((\d+)\)", line_s)
                            if m_bat:
                                dev["battery_level"] = int(m_bat.group(1))
            except Exception as e:
                logger.debug("bluetoothctl info %s failed: %s", mac, e)

        # Classify Sony characteristics and BLE
        name_str = (dev["name"] or "") + " " + (dev["alias"] or "")
        name_upper = name_str.upper()

        # Check BLE indicator (LE prefix on device name)
        name_clean = dev["name"].strip().upper()
        alias_clean = dev["alias"].strip().upper()
        dev["is_le"] = (
            name_clean.startswith("LE_")
            or name_clean.startswith("LE-")
            or name_clean.startswith("LE ")
            or alias_clean.startswith("LE_")
            or alias_clean.startswith("LE-")
        )

        # Check Sony indicator
        matches_sony_name = any(kw in name_upper for kw in SONY_NAME_KEYWORDS)
        matches_sony_uuid = any(any(su in u for su in SONY_UUIDS) for u in dev["uuids"])
        dev["is_sony"] = matches_sony_name or matches_sony_uuid

        results.append(dev)

    return results


def find_connected_sony_device() -> tuple[str | None, str | None]:
    """Scan connected Bluetooth devices and locate the best candidate Sony WH/WF headphones.

    Explicitly prioritizes Classic Bluetooth (BR/EDR) MAC addresses over BLE addresses,
    because RFCOMM sockets only operate over Classic Bluetooth.

    Returns:
        (mac_address, device_name) or (None, None) if no Sony device is detected.
    """
    devices = scan_all_bluetooth_devices()
    if not devices:
        logger.debug("No Bluetooth devices returned during scan")
        return None, None

    logger.debug(
        "Discovered %d Bluetooth devices in scan: %s",
        len(devices),
        [d["name"] for d in devices],
    )

    # Rank 1: Connected Sony Classic Bluetooth (Not LE) -> Highest priority
    for d in devices:
        if d["connected"] and d["is_sony"] and not d["is_le"]:
            logger.info("Found connected Sony Classic device: %s (%s)", d["name"], d["mac"])
            return d["mac"], d["name"]

    # Rank 2: Connected Sony LE (Fallback if no separate Classic entry listed)
    for d in devices:
        if d["connected"] and d["is_sony"] and d["is_le"]:
            logger.info("Found connected Sony LE device: %s (%s)", d["name"], d["mac"])
            return d["mac"], d["name"]

    # Rank 3: Connected audio headphone device that might be Sony with a custom name
    for d in devices:
        if d["connected"] and not d["is_le"] and ("headphone" in d["icon"] or "audio" in d["icon"]):
            logger.info("Found connected audio headphone candidate: %s (%s)", d["name"], d["mac"])
            return d["mac"], d["name"]

    # Rank 4: Paired Sony Classic device (in case BlueZ connection status is delayed)
    for d in devices:
        if d["is_sony"] and not d["is_le"]:
            logger.info("Found paired Sony Classic candidate: %s (%s)", d["name"], d["mac"])
            return d["mac"], d["name"]

    return None, None


def find_rfcomm_channel(mac: str) -> int | None:
    """Query SDP records on remote device to dynamically discover the Sony MDR RFCOMM channel.

    Returns:
        Channel number (1-30) or None if not discovered.
    """
    try:
        proc = subprocess.run(
            ["sdptool", "browse", mac],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout:
            return None

        # Split SDP output into service blocks
        blocks = proc.stdout.split("Service Name:")
        for block in blocks:
            block_lower = block.lower()
            # Match Sony MDR UUIDs or Sony signatures
            if any(u in block_lower for u in SONY_UUIDS) or "sony" in block_lower:
                m = re.search(r"Channel:\s*(\d+)", block, re.IGNORECASE)
                if m:
                    ch = int(m.group(1))
                    logger.info("SDP discovered RFCOMM channel %d for %s", ch, mac)
                    return ch

    except Exception as e:
        logger.debug("SDP browse query failed for %s: %s", mac, e)

    return None


class SonyConnection:
    """Manages an active RFCOMM socket to a Sony MDR headset."""

    def __init__(self) -> None:
        self.mac: str | None = None
        self.device_name: str | None = None
        self.channel: int | None = None
        self.connected: bool = False
        self.is_busy: bool = False
        self.last_error: str | None = None

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
        channel: int | None = None,
        name: str | None = None,
    ) -> bool:
        """Establish RFCOMM socket connection to the specified Sony MAC address.

        Attempts dynamic SDP channel detection and falls back to candidate channels.
        """
        async with self._lock:
            if self.connected:
                return True

            if not is_rfcomm_supported():
                self.last_error = "Native AF_BLUETOOTH RFCOMM not supported on platform"
                logger.warning(self.last_error)
                self.is_busy = False
                return False

            self.mac = mac
            self.device_name = name or "Sony Headphones"
            self.is_busy = False
            self.last_error = None

            loop = asyncio.get_running_loop()

            # Determine candidate channels to try
            candidate_channels: list[int] = []
            if channel is not None:
                candidate_channels.append(channel)
            else:
                sdp_ch = await loop.run_in_executor(None, find_rfcomm_channel, mac)
                if sdp_ch:
                    candidate_channels.append(sdp_ch)
                for ch in FALLBACK_RFCOMM_CHANNELS:
                    if ch not in candidate_channels:
                        candidate_channels.append(ch)

            last_exc: Exception | None = None

            for ch in candidate_channels:
                try:
                    logger.debug("Attempting RFCOMM connect to %s on channel %d...", mac, ch)
                    sock = await loop.run_in_executor(None, self._sync_connect, mac, ch)
                    sock.setblocking(False)
                    self._socket = sock
                    self.channel = ch
                    self.connected = True
                    self._parser.reset()
                    self._arq.sm.reset()

                    # Start background reader task
                    self._reader_task = asyncio.create_task(self._socket_reader_loop())

                    logger.info("Successfully connected to Sony MDR at %s (channel %d)", mac, ch)

                    # Populate initial battery from BlueZ if available
                    if self.battery_status.battery_level is None:
                        for d in scan_all_bluetooth_devices():
                            if d.get("mac") == mac and d.get("battery_level") is not None:
                                self.battery_status = BatteryStatus(
                                    battery_level=d["battery_level"], charging=False
                                )
                                logger.info(
                                    "Initial battery populated from BlueZ: %d%%",
                                    d["battery_level"],
                                )
                                break

                    # Query initial states
                    asyncio.create_task(self._query_initial_states())
                    self._notify("connected", True)
                    return True

                except OSError as e:
                    last_exc = e
                    err_num = getattr(e, "errno", None)
                    logger.debug(
                        "Failed connect to %s channel %d (errno %s): %s",
                        mac,
                        ch,
                        err_num,
                        e,
                    )

                    # If channel is locked by smartphone app
                    if err_num in (16, 114):  # EBUSY or EALREADY
                        self.is_busy = True
                        self.last_error = "RFCOMM Port Busy (locked by smartphone app)"
                        break

            # If all candidate channels failed
            err_num = getattr(last_exc, "errno", None) if last_exc else None
            if err_num in (111, 104):  # ECONNREFUSED or ECONNRESET
                self.is_busy = True
                self.last_error = (
                    f"Connection refused on all channels for {mac}. "
                    "Your headphones may be connected to the Sony app on your phone."
                )
            elif err_num in (112, 113):  # EHOSTDOWN or ENETUNREACH
                self.last_error = (
                    f"Headphones unreachable at {mac}. Ensure headphones are turned on."
                )
            else:
                self.last_error = f"Bluetooth error [{err_num}]: {last_exc}"

            logger.warning("All RFCOMM connection attempts failed for %s: %s", mac, self.last_error)
            await self.disconnect()
            return False

    def _sync_connect(self, mac: str, channel: int) -> socket.socket:
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.settimeout(2.0)
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
