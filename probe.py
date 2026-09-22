#!/usr/bin/env python3
"""Standalone diagnostic tool to probe RFCOMM channels and Sony MDR protocol on SteamOS."""

import socket
import sys
import time

MAC = "AA:BB:CC:DD:EE:FF"
if len(sys.argv) > 1:
    MAC = sys.argv[1]

print(f"==================================================")
print(f"XMDeck Diagnostic Probe targeting: {MAC}")
print(f"==================================================")

# Check AF_BLUETOOTH support
if not hasattr(socket, "AF_BLUETOOTH") or not hasattr(socket, "BTPROTO_RFCOMM"):
    print("ERROR: Native AF_BLUETOOTH RFCOMM is NOT supported by this Python runtime.")
    sys.exit(1)

print("Native AF_BLUETOOTH RFCOMM is available.\n")
print(f"Probing RFCOMM channels 1 through 30 on {MAC}...")

successful_channel = None

for ch in range(1, 31):
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    sock.settimeout(0.7)
    try:
        sock.connect((MAC, ch))
        print(f"  >>> CHANNEL {ch}: CONNECTED SUCCESS! <<<")
        successful_channel = ch
        
        # Test sending a Sony MDR Table 1 Battery query
        # Frame format: 0x3E [DataType=0x0C] [Seq=0x00] [Len=0x02] [Table=0x02] [Inquiry=0x22] [Checksum] 0x3C
        # Query bytes: 0x02, 0x22
        payload = bytes([0x02, 0x22])
        # Additive checksum: sum of payload modulo 256
        chk = (0x0C + 0x00 + len(payload) + sum(payload)) % 256
        test_frame = bytes([0x3E, 0x0C, 0x00, len(payload)]) + payload + bytes([chk, 0x3C])
        
        print(f"      Sending Sony battery query to channel {ch}...")
        sock.sendall(test_frame)
        
        sock.settimeout(1.5)
        response = sock.recv(128)
        print(f"      Received {len(response)} bytes: {response.hex(' ')}")
        sock.close()
        break
    except Exception as e:
        err = getattr(e, "errno", None)
        err_msg = str(e)
        if err in (111,):
            print(f"  Channel {ch:2d}: Refused (errno 111) - port closed or locked by another app")
        elif err in (16, 114):
            print(f"  Channel {ch:2d}: BUSY (errno {err}) - locked by smartphone app")
        elif err in (112, 113):
            print(f"  Channel {ch:2d}: Host down / unreachable (errno {err})")
            break
        else:
            print(f"  Channel {ch:2d}: {type(e).__name__} (errno {err}): {err_msg}")
    finally:
        try:
            sock.close()
        except Exception:
            pass

print("\n==================================================")
if successful_channel is not None:
    print(f"RESULT: Found working Sony MDR RFCOMM on CHANNEL {successful_channel}!")
else:
    print("RESULT: No open RFCOMM channel found.")
    print("Troubleshooting tips:")
    print("1. If all channels show 'Refused (errno 111)' or 'BUSY (errno 16)':")
    print("   Your headphones are connected to your smartphone's Sony app.")
    print("   Turn OFF Bluetooth on your phone for 10 seconds, then re-run this script.")
    print("2. Ensure headphones are paired and connected in SteamOS Bluetooth settings.")
print("==================================================")
