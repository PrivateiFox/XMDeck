"""Sony MDR Protocol V2 packet schemas, encoders, and decoders.

Provides structured serialization/deserialization for:
- Battery status & charging indicators (single and dual earbud).
- ANC Mode (Cancelling, Ambient, Off).
- Ambient Sound Level (1-20) and Focus on Voice.
- Speak-to-Chat (Smart Talking Mode).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Literal


class FrameDataType(IntEnum):
    """Sony MDR V2 frame data types."""

    DATA = 0x00
    ACK = 0x01
    DATA_MDR = 0x0C  # 12: Standard data requiring ACK
    DATA_COMMON = 0x0D  # 13
    DATA_MDR_NO2 = 0x0E  # 14: Data requiring ACK (table 2)
    SHOT_MDR = 0x1C  # 28: Unacknowledged shot command
    SHOT_MDR_NO2 = 0x1E  # 30: Unacknowledged shot command (table 2)


class CommandTable1(IntEnum):
    """Sony MDR V2 Table 1 command opcodes."""

    # Power / Battery
    POWER_GET_STATUS = 0x22  # 34
    POWER_RET_STATUS = 0x23  # 35
    POWER_SET_STATUS = 0x24  # 36
    POWER_NTFY_STATUS = 0x25  # 37

    # Noise Cancelling / Ambient Sound
    NCASM_GET_PARAM = 0x66  # 102
    NCASM_RET_PARAM = 0x67  # 103
    NCASM_SET_PARAM = 0x68  # 104
    NCASM_NTFY_PARAM = 0x69  # 105

    # System / Speak-to-Chat
    SYSTEM_GET_PARAM = 0xF6  # 246
    SYSTEM_RET_PARAM = 0xF7  # 247
    SYSTEM_SET_PARAM = 0xF8  # 248
    SYSTEM_NTFY_PARAM = 0xF9  # 249


class PowerInquiredType(IntEnum):
    """Power query sub-types."""

    BATTERY = 0x00
    LEFT_RIGHT_BATTERY = 0x01
    CRADLE_BATTERY = 0x02


class BatteryChargingStatus(IntEnum):
    """Charging states reported by Sony MDR."""

    NOT_CHARGING = 0
    CHARGING = 1
    UNKNOWN = 2
    CHARGED = 3


class NcAsmInquiredType(IntEnum):
    """NC/ASM inquiry types."""

    NC_ON_OFF = 0x01
    NC_MODE_SWITCH_AND_ASM_SEAMLESS = 0x14  # 20
    MODE_NC_ASM_DUAL_NC_MODE_SWITCH_AND_ASM_SEAMLESS = 0x17  # 23


class NcAsmOnOffValue(IntEnum):
    """Total effect on/off."""

    OFF = 0x00
    ON = 0x01


class NcAsmMode(IntEnum):
    """Noise Cancelling vs Ambient Sound Mode."""

    NC = 0x00
    ASM = 0x01


class AmbientSoundMode(IntEnum):
    """Normal ambient sound vs Focus on Voice."""

    NORMAL = 0x00
    VOICE = 0x01


class SystemInquiredType(IntEnum):
    """System inquired types."""

    SMART_TALKING_MODE_TYPE2 = 0x0C  # Speak-to-Chat in V2


class OnOffSettingValue(IntEnum):
    """Generic ON/OFF parameter setting."""

    ON = 0x00
    OFF = 0x01


ANCModeLiteral = Literal["cancelling", "ambient", "off"]


@dataclass(frozen=True, slots=True)
class BatteryStatus:
    """Parsed battery and charging information."""

    battery_level: int | None
    charging: bool
    left_level: int | None = None
    right_level: int | None = None
    left_charging: bool | None = None
    right_charging: bool | None = None


@dataclass(frozen=True, slots=True)
class ANCState:
    """Parsed Active Noise Cancellation & Ambient Sound state."""

    mode: ANCModeLiteral
    ambient_level: int
    voice_focus: bool


# ---------------------------------------------------------------------------
# Battery Queries & Encoders/Decoders
# ---------------------------------------------------------------------------


def build_battery_query(inquired_type: PowerInquiredType = PowerInquiredType.BATTERY) -> bytes:
    """Build query payload for battery status."""
    return bytes([CommandTable1.POWER_GET_STATUS, inquired_type])


def parse_battery_status(payload: bytes) -> BatteryStatus:
    """Parse Sony MDR battery response or notification payload.

    Supports both single battery (headphones) and L/R battery (earbuds).
    """
    if len(payload) < 2:
        return BatteryStatus(battery_level=None, charging=False)

    cmd = payload[0]
    if cmd not in (CommandTable1.POWER_RET_STATUS, CommandTable1.POWER_NTFY_STATUS):
        return BatteryStatus(battery_level=None, charging=False)

    inquired_type = payload[1]

    if inquired_type == PowerInquiredType.BATTERY and len(payload) >= 4:
        level = payload[2]
        charging = payload[3] in (
            BatteryChargingStatus.CHARGING,
            BatteryChargingStatus.CHARGED,
        )
        # Level 255 indicates unknown/not reported
        valid_level = level if level <= 100 else None
        return BatteryStatus(battery_level=valid_level, charging=charging)

    if inquired_type == PowerInquiredType.LEFT_RIGHT_BATTERY and len(payload) >= 6:
        l_level = payload[2] if payload[2] <= 100 else None
        l_charging = payload[3] in (
            BatteryChargingStatus.CHARGING,
            BatteryChargingStatus.CHARGED,
        )
        r_level = payload[4] if payload[4] <= 100 else None
        r_charging = payload[5] in (
            BatteryChargingStatus.CHARGING,
            BatteryChargingStatus.CHARGED,
        )

        # Synthesize overall battery level (average of non-None earbud levels)
        levels = [x for x in (l_level, r_level) if x is not None]
        avg_level = sum(levels) // len(levels) if levels else None
        overall_charging = bool(l_charging or r_charging)

        return BatteryStatus(
            battery_level=avg_level,
            charging=overall_charging,
            left_level=l_level,
            right_level=r_level,
            left_charging=l_charging,
            right_charging=r_charging,
        )

    return BatteryStatus(battery_level=None, charging=False)


# ---------------------------------------------------------------------------
# ANC & Ambient Sound Queries & Encoders/Decoders
# ---------------------------------------------------------------------------


DEFAULT_NC_ASM_TYPE = NcAsmInquiredType.MODE_NC_ASM_DUAL_NC_MODE_SWITCH_AND_ASM_SEAMLESS


def build_anc_query(inquired_type: NcAsmInquiredType = DEFAULT_NC_ASM_TYPE) -> bytes:
    """Build query payload for ANC/Ambient sound parameters."""
    return bytes([CommandTable1.NCASM_GET_PARAM, inquired_type])


def parse_anc_state(payload: bytes) -> ANCState | None:
    """Parse Sony MDR ANC/Ambient response or notification payload."""
    if len(payload) < 7:
        return None

    cmd = payload[0]
    if cmd not in (CommandTable1.NCASM_RET_PARAM, CommandTable1.NCASM_NTFY_PARAM):
        return None

    inquired_type = payload[1]
    if inquired_type not in (
        NcAsmInquiredType.MODE_NC_ASM_DUAL_NC_MODE_SWITCH_AND_ASM_SEAMLESS,
        NcAsmInquiredType.NC_MODE_SWITCH_AND_ASM_SEAMLESS,
    ):
        return None

    # Minimum struct length: cmd(1) + type(1) + status(1) + onOff(1) + mode(1) + asm(1) + val(1) = 7
    total_effect = payload[3]
    nc_mode = payload[4]
    asm_mode = payload[5]
    asm_level = payload[6]

    voice_focus = asm_mode == AmbientSoundMode.VOICE
    clamped_level = max(1, min(20, asm_level)) if asm_level > 0 else 1

    if total_effect == NcAsmOnOffValue.OFF:
        mode: ANCModeLiteral = "off"
    elif nc_mode == NcAsmMode.NC:
        mode = "cancelling"
    else:
        mode = "ambient"

    return ANCState(mode=mode, ambient_level=clamped_level, voice_focus=voice_focus)


def build_set_anc_mode(
    mode: str,
    ambient_level: int = 1,
    voice_focus: bool = False,
    inquired_type: int = DEFAULT_NC_ASM_TYPE,
) -> bytes:
    """Build command payload to set Active Noise Cancellation mode.

    Args:
        mode: "cancelling", "ambient", or "off".
        ambient_level: Ambient transparency level (1-20).
        voice_focus: True to enhance voices in ambient mode.
        inquired_type: Sony MDR inquired type.
    """
    clamped_level = max(1, min(20, ambient_level))
    voice_mode = AmbientSoundMode.VOICE if voice_focus else AmbientSoundMode.NORMAL

    if mode == "cancelling":
        total_effect = NcAsmOnOffValue.ON
        nc_mode = NcAsmMode.NC
        level_val = 0
    elif mode == "ambient":
        total_effect = NcAsmOnOffValue.ON
        nc_mode = NcAsmMode.ASM
        level_val = clamped_level
    else:  # "off"
        total_effect = NcAsmOnOffValue.OFF
        nc_mode = NcAsmMode.NC
        level_val = 0

    return bytes(
        [
            CommandTable1.NCASM_SET_PARAM,
            inquired_type,
            0x01,  # ValueChangeStatus: CHANGED
            total_effect,
            nc_mode,
            voice_mode,
            level_val,
        ]
    )


def build_set_ambient_sound(
    level: int,
    voice_focus: bool,
    inquired_type: int = DEFAULT_NC_ASM_TYPE,
) -> bytes:
    """Build command payload to adjust Ambient Sound level and Voice Focus."""
    return build_set_anc_mode(
        "ambient", ambient_level=level, voice_focus=voice_focus, inquired_type=inquired_type
    )


# ---------------------------------------------------------------------------
# Speak-to-Chat Queries & Encoders/Decoders
# ---------------------------------------------------------------------------


def build_speak_to_chat_query() -> bytes:
    """Build query payload for Speak-to-Chat (Smart Talking Mode)."""
    return bytes([CommandTable1.SYSTEM_GET_PARAM, SystemInquiredType.SMART_TALKING_MODE_TYPE2])


def parse_speak_to_chat(payload: bytes) -> bool | None:
    """Parse Sony MDR Speak-to-Chat status from response or notification."""
    if len(payload) < 3:
        return None

    cmd = payload[0]
    if cmd not in (CommandTable1.SYSTEM_RET_PARAM, CommandTable1.SYSTEM_NTFY_PARAM):
        return None

    if payload[1] != SystemInquiredType.SMART_TALKING_MODE_TYPE2:
        return None

    on_off = payload[2]
    return on_off == OnOffSettingValue.ON


def build_set_speak_to_chat(enabled: bool) -> bytes:
    """Build command payload to enable/disable Speak-to-Chat."""
    on_off = OnOffSettingValue.ON if enabled else OnOffSettingValue.OFF
    return bytes(
        [
            CommandTable1.SYSTEM_SET_PARAM,
            SystemInquiredType.SMART_TALKING_MODE_TYPE2,
            on_off,
            OnOffSettingValue.OFF,  # previewModeOnOffValue
        ]
    )
