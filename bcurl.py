#!/usr/bin/env python3
"""
bcurl.py - a tiny curl for our binary HTTP (see SPEC.md).

    python bcurl.py localhost:9000/index.html
    python bcurl.py -v localhost:9000/index.html     # also hexdump every frame

The body goes to stdout. The -v hexdump goes to stderr, so it doesn't mix
with the body. Exit code is 1 if the status is 4xx or 5xx, otherwise 0.
"""
import socket
import struct
import sys

FRAME_HEADER = struct.Struct(">IBB")   # length (4 bytes), type (1), flags (1)
DATA, HEADERS = 0, 1                   # frame types
END = 1                                # flag: last frame of this message

# header names we send often get a number. 0 = "the name is written out".
NAMES = [None, ":method", ":path", ":status", "host", "user-agent", "accept",
         "content-type", "content-length", "server", "date"]


def recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("server closed the connection")
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
    headers = {}
    pos = 0
    while pos < len(block):
        index = block[pos]
        pos += 1
        if index == 0:
            name = block[pos + 1:pos + 1 + block[pos]].decode()
            pos += 1 + block[pos]
        else:
            name = NAMES[index]
        length = int.from_bytes(block[pos:pos + 2], "big")
        headers[name] = block[pos + 2:pos + 2 + length].decode()
        pos += 2 + length
    return headers


def hexdump(arrow, frame):
    length, ftype, flags = FRAME_HEADER.unpack(frame[:6])
    print(f"{arrow} frame: length={length} type={ftype} flags={flags}", file=sys.stderr)
    for i in range(0, len(frame), 16):
        row = frame[i:i + 16]
        hexes = " ".join(f"{b:02x}" for b in row)
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        print(f"{arrow} {i:04x}  {hexes:<47}  {text}", file=sys.stderr)


def read_response(sock, verbose=False):
    """Read frames until one has the END flag. -> (status, body)"""
    status, body = None, b""
    while True:
        head = recv_exact(sock, 6)
        length, ftype, flags = FRAME_HEADER.unpack(head)
        payload = recv_exact(sock, length)
        if verbose:
            hexdump("<", head + payload)
        if ftype == HEADERS:
            status = int(decode_headers(payload)[":status"])
        elif ftype == DATA:
            body += payload
        else:
            continue   # unknown frame type: skip it
        if flags & END:
            return status, body


if __name__ == "__main__":
    verbose = "-v" in sys.argv
    args = [a for a in sys.argv[1:] if a != "-v"]
    if len(args) != 1:
        sys.exit("usage: python bcurl.py [-v] host:port/path")

    hostport, _, path = args[0].partition("/")
    host, _, port = hostport.partition(":")
    path = "/" + path

    sock = socket.create_connection((host, int(port or 9000)))   # the only connection
    headers = encode_headers([(":method", "GET"), (":path", path), ("host", hostport),
                              ("user-agent", "bcurl/1"), ("accept", "*/*")])
    request = FRAME_HEADER.pack(len(headers), HEADERS, END) + headers
    if verbose:
        hexdump(">", request)
    sock.sendall(request)

    status, body = read_response(sock, verbose)
    sock.close()
    sys.stdout.buffer.write(body)
    sys.exit(1 if status >= 400 else 0)
