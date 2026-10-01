#!/usr/bin/env python3
"""
bserve.py - a file server that speaks our binary HTTP (see SPEC.md).

    python bserve.py ./www 9000

    file exists       -> 200 + the file
    file not there    -> 404
    malformed frame   -> 400

The connection stays open after every reply, even after a 400. Every frame
starts with its length, so we always know where the next frame begins.

Only the socket module + one thread per connection. No framework.
"""
import mimetypes
import os
import socket
import struct
import sys
import threading
from email.utils import formatdate

FRAME_HEADER = struct.Struct(">IBB")   # length (4 bytes), type (1), flags (1)
DATA, HEADERS = 0, 1                   # frame types
END = 1                                # flag: last frame of this message

# header names we send often get a number. 0 = "the name is written out".
NAMES = [None, ":method", ":path", ":status", "host", "user-agent", "accept",
         "content-type", "content-length", "server", "date"]

IDLE_TIMEOUT = 15   # close a connection that has been silent this many seconds


def recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("client closed the connection")
        data += chunk
    return data


def encode_headers(headers):
    out = b""
    for name, value in headers:
        if name in NAMES:
            out += bytes([NAMES.index(name)])
        else:
            out += bytes([0, len(name)]) + name.encode()
        out += len(value).to_bytes(2, "big") + value.encode()
    return out


def decode_headers(block):
    """Raises ValueError if the block is malformed."""
    headers = {}
    pos = 0

    def take(n):
        nonlocal pos
        if pos + n > len(block):
            raise ValueError("header block is cut short")
        pos += n
        return block[pos - n:pos]

    while pos < len(block):
        index = take(1)[0]
        if index == 0:
            name = take(take(1)[0]).decode()
        elif index < len(NAMES):
            name = NAMES[index]
        else:
            raise ValueError(f"unknown header number {index}")
        headers[name] = take(int.from_bytes(take(2), "big")).decode()
    return headers


def read_request(sock):
    """Read frames until one has the END flag. Returns the headers.

    A malformed request is still read to the end before we raise
    ValueError, so the next request starts at a frame boundary.
    """
    headers, problem = None, None
    while True:
        length, ftype, flags = FRAME_HEADER.unpack(recv_exact(sock, 6))
        payload = recv_exact(sock, length)
        if ftype == HEADERS:
            try:
                headers = decode_headers(payload)
            except ValueError as e:
                problem = str(e)
        elif ftype == DATA:
            if headers is None:
                problem = "DATA frame before HEADERS"
        else:
            continue   # unknown frame type: skip it (we already read its payload)
        if flags & END:
            break
    if problem:
        raise ValueError(problem)
    if ":path" not in headers:
        raise ValueError("no :path")
    return headers


def find_file(root, path):
    """URL path -> file inside root, or None."""
    full = os.path.realpath(os.path.join(root, path.lstrip("/")))
    if full.startswith(root + os.sep) and os.path.isfile(full):
        return full
    return None   # not there, or outside the root (like /../secret)


def send(sock, status, body, content_type="text/plain"):
    head = encode_headers([(":status", str(status)), ("content-type", content_type),
                           ("content-length", str(len(body))), ("server", "bserve/1"),
                           ("date", formatdate(usegmt=True))])
    sock.sendall(FRAME_HEADER.pack(len(head), HEADERS, 0) + head
                 + FRAME_HEADER.pack(len(body), DATA, END) + body)


def handle(sock, root, conn_id):
    sock.settimeout(IDLE_TIMEOUT)
    try:
        while True:
            try:
                path = read_request(sock)[":path"]
            except ValueError as e:
                send(sock, 400, f"bad request: {e}\n".encode())
                print(f"conn {conn_id}: 400 {e}")
                continue                  # keep the connection open
            full = find_file(root, path)
            if full is None:
                send(sock, 404, f"not found: {path}\n".encode())
                print(f"conn {conn_id}: {path} -> 404")
            else:
                with open(full, "rb") as f:
                    send(sock, 200, f.read(), mimetypes.guess_type(full)[0] or "application/octet-stream")
                print(f"conn {conn_id}: {path} -> 200")
    except OSError:
        pass   # client went away or was idle too long
    finally:
        sock.close()
        print(f"conn {conn_id}: closed")


def serve(listener, root):
    root = os.path.realpath(root)
    listener.settimeout(1)   # wake up every second so Ctrl+C works on Windows
    conn_id = 0
    while True:
        try:
            sock, addr = listener.accept()
        except TimeoutError:
            continue
        conn_id += 1
        print(f"conn {conn_id}: opened from {addr}")
        threading.Thread(target=handle, args=(sock, root, conn_id), daemon=True).start()


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "./www"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9000
    print(f"serving {root} on port {port}")
    try:
        # IPv4 + IPv6, because "localhost" may mean 127.0.0.1 or ::1
        serve(socket.create_server(("", port), family=socket.AF_INET6, dualstack_ipv6=True), root)
    except KeyboardInterrupt:
        pass
