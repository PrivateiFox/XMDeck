#!/usr/bin/env python3
"""Standalone diagnostic tool to probe RFCOMM channels and Sony MDR protocol on SteamOS."""

import socket
import sys
import time

from backend.protocol.framing import StreamParser, encode_frame
from backend.protocol.messages import (
    build_anc_query,
    build_battery_query,
    parse_anc_state,
    parse_battery_status,
)

MAC = "80:99:E7:E7:1E:C4"
if len(sys.argv) > 1:
    MAC = sys.argv[1]

print("==================================================")
print(f"XMDeck Diagnostic Probe targeting: {MAC}")
print("==================================================")

# Check AF_BLUETOOTH support
if not hasattr(socket, "AF_BLUETOOTH") or not hasattr(socket, "BTPROTO_RFCOMM"):
    print("ERROR: Native AF_BLUETOOTH RFCOMM is NOT supported by this Python runtime.")
    sys.exit(1)

print("Native AF_BLUETOOTH RFCOMM is available.\n")
print(f"Connecting to RFCOMM Channel 9 on {MAC}...")

sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
sock.settimeout(2.0)

try:
    sock.connect((MAC, 9))
    print("  >>> CHANNEL 9 CONNECTED SUCCESSFUL! <<<")

    parser = StreamParser()

    # 1. Send Battery Query (MDR Table 1)
    battery_cmd = build_battery_query()
    battery_frame = encode_frame(0x0C, 0, battery_cmd)
    print(f"\n[1] Sending Battery Query: {battery_frame.hex(' ')}")
    sock.sendall(battery_frame)

    # Read response
    sock.settimeout(2.0)
    data = sock.recv(1024)
    print(f"    Raw bytes received ({len(data)}B): {data.hex(' ')}")
    frames = parser.feed(data)
    for f in frames:
        print(f"    Decoded: type=0x{f.data_type:02X}, seq={f.seq}, payload={f.payload.hex(' ')}")
        battery = parse_battery_status(f.payload)
        if battery.battery_level is not None:
            print(f"    >>> BATTERY: {battery.battery_level}% (Charging: {battery.charging}) <<<")

    time.sleep(0.2)

    # 2. Send ANC State Query
    anc_cmd = build_anc_query()
    anc_frame = encode_frame(0x0C, 1, anc_cmd)
    print(f"\n[2] Sending ANC State Query: {anc_frame.hex(' ')}")
    sock.sendall(anc_frame)

    data = sock.recv(1024)
    print(f"    Raw bytes received ({len(data)}B): {data.hex(' ')}")
    frames = parser.feed(data)
    for f in frames:
        print(f"    Decoded: type=0x{f.data_type:02X}, seq={f.seq}, payload={f.payload.hex(' ')}")
        anc = parse_anc_state(f.payload)
        if anc.mode is not None:
            print(f"    >>> ANC: mode={anc.mode}, lvl={anc.ambient_level} <<<")

    sock.close()
    print("\n==================================================")
    print("RESULT: SUCCESS! Communication with Sony WH-1000XM6 verified on Channel 9!")
    print("==================================================")

except Exception as e:
    err = getattr(e, "errno", None)
    print(f"\nError: {type(e).__name__} (errno {err}): {e}")
    if err in (111, 16):
        print("Tip: Port is busy or refused. Turn off Bluetooth on your phone.")
    sock.close()
