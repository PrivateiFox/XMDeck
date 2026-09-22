#!/usr/bin/env python3
"""Standalone RFCOMM-to-Unix-socket bridge executed via system /usr/bin/python3.

Used when Decky Loader's embedded Python runtime lacks AF_BLUETOOTH / BTPROTO_RFCOMM support.
"""

from __future__ import annotations

import os
import select
import socket
import sys

AF_BLUETOOTH = getattr(socket, "AF_BLUETOOTH", 31)
BTPROTO_RFCOMM = getattr(socket, "BTPROTO_RFCOMM", 3)
AF_UNIX = getattr(socket, "AF_UNIX", 1)


def run_bridge(mac: str, channel: int, unix_sock_path: str) -> None:
    if os.path.exists(unix_sock_path):
        try:
            os.unlink(unix_sock_path)
        except OSError:
            pass

    rfcomm_sock: socket.socket | None = None
    server_sock: socket.socket | None = None
    client_sock: socket.socket | None = None

    try:
        # 1. Connect to Sony RFCOMM
        rfcomm_sock = socket.socket(AF_BLUETOOTH, socket.SOCK_STREAM, BTPROTO_RFCOMM)
        rfcomm_sock.settimeout(3.0)
        rfcomm_sock.connect((mac, channel))

        # 2. Setup Unix Domain server socket
        server_sock = socket.socket(AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind(unix_sock_path)
        server_sock.listen(1)
        server_sock.settimeout(5.0)

        # Signal parent process that we are connected and listening
        print("READY", flush=True)

        # 3. Accept Decky plugin connection
        client_sock, _ = server_sock.accept()

        rfcomm_sock.setblocking(False)
        client_sock.setblocking(False)

        sockets = [rfcomm_sock, client_sock]

        while True:
            rlist, _, xlist = select.select(sockets, [], sockets, 1.0)
            if xlist:
                break
            for s in rlist:
                data = s.recv(4096)
                if not data:
                    return
                if s is rfcomm_sock:
                    client_sock.sendall(data)
                else:
                    rfcomm_sock.sendall(data)

    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        sys.exit(1)
    finally:
        if rfcomm_sock:
            try:
                rfcomm_sock.close()
            except Exception:
                pass
        if client_sock:
            try:
                client_sock.close()
            except Exception:
                pass
        if server_sock:
            try:
                server_sock.close()
            except Exception:
                pass
        if os.path.exists(unix_sock_path):
            try:
                os.unlink(unix_sock_path)
            except OSError:
                pass


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: bridge.py <mac> <channel> <unix_socket_path>", file=sys.stderr)
        sys.exit(1)
    run_bridge(sys.argv[1], int(sys.argv[2]), sys.argv[3])
