# HTTP, in binary

A small binary version of HTTP, with a file server (`bserve`) and a client
(`bcurl`) that use it. Written with only Python's `socket` module. No
framework.

What I hand in:

1. [SPEC.md](SPEC.md): the spec
2. [bserve.py](bserve.py) (server) and [bcurl.py](bcurl.py) (client): the programs
3. [HEXDUMP.md](HEXDUMP.md): one request and response, explained byte by byte

## Run it

You need Python 3.10 or newer. Nothing else to install.

```sh
python bserve.py ./www 9000
python bcurl.py -v localhost:9000/index.html
```

| Server reply | When |
|---|---|
| 200 + file | the file exists in the root folder |
| 404 | the file isn't there |
| 400 | the frame is malformed |

The connection stays open after every reply.

## Tests

```sh
python test_bhttp.py
```

## Files

- `bserve.py`: the server
- `bcurl.py`: the client
- `test_bhttp.py`: 3 tests over real sockets (200/404/400 on one connection,
  an unknown frame type being skipped, and bcurl's exit codes)
- `www/index.html`: a page to serve
