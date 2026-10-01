#!/usr/bin/env python3
"""
test_bhttp.py - starts bserve in a thread and talks to it over real sockets.

    python test_bhttp.py
"""
import socket
import subprocess
import sys
import threading

import bcurl
import bserve

listener = socket.create_server(("127.0.0.1", 0))   # port 0 = any free port
PORT = listener.getsockname()[1]
threading.Thread(target=bserve.serve, args=(listener, "www"), daemon=True).start()


def headers_frame(block):
    return bcurl.FRAME_HEADER.pack(len(block), bcurl.HEADERS, bcurl.END) + block


def get(path):
    return headers_frame(bcurl.encode_headers([(":method", "GET"), (":path", path)]))


def ask(sock, raw):
    sock.sendall(raw)
    return bcurl.read_response(sock)[0]


def test_one_connection():
    s = socket.create_connection(("127.0.0.1", PORT))
    assert ask(s, get("/index.html")) == 200
    assert ask(s, get("/missing.html")) == 404
    assert ask(s, get("/../bserve.py")) == 404             # can't leave the root folder
    assert ask(s, headers_frame(b"\xc8\x00\x01x")) == 400  # header number 200 doesn't exist
    assert ask(s, get("/index.html")) == 200               # still open after the 400
    s.close()


def test_unknown_frame_is_skipped():
    s = socket.create_connection(("127.0.0.1", PORT))
    unknown = bcurl.FRAME_HEADER.pack(5, 99, 0) + b"hello"   # type 99 doesn't exist
    assert ask(s, unknown + get("/index.html")) == 200
    s.close()


def test_bcurl_exit_code():
    def bcurl_run(path):
        return subprocess.run([sys.executable, "bcurl.py", f"localhost:{PORT}{path}"],
                              capture_output=True).returncode
    assert bcurl_run("/index.html") == 0
    assert bcurl_run("/missing.html") == 1


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in list(globals().items()) if name.startswith("test_")]
    for name, fn in tests:
        print(name)
        fn()
    print(f"\nall {len(tests)} tests passed")
