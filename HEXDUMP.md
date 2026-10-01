# Annotated hexdump: one request and response

Real output of:

```sh
python bserve.py ./www 9000
python bcurl.py -v localhost:9000/index.html
```

`>` = bytes bcurl sent, `<` = bytes bcurl received. Offsets are in hex.

## Request: HEADERS frame (59 bytes)

```
> frame: length=53 type=1 flags=1
> 0000  00 00 00 35 01 01 01 00 03 47 45 54 02 00 0b 2f  ...5.....GET.../
> 0010  69 6e 64 65 78 2e 68 74 6d 6c 04 00 0e 6c 6f 63  index.html...loc
> 0020  61 6c 68 6f 73 74 3a 39 30 30 30 05 00 07 62 63  alhost:9000...bc
> 0030  75 72 6c 2f 31 06 00 03 2a 2f 2a                 url/1...*/*
```

| Offset | Bytes | Meaning |
|---|---|---|
| 00-03 | `00 00 00 35` | Length = 0x35 = 53 bytes of payload |
| 04 | `01` | Type = HEADERS |
| 05 | `01` | Flags = END (no body, the request is complete) |
| 06 | `01` | name #1 `:method` |
| 07-08 | `00 03` | value is 3 bytes |
| 09-0b | `47 45 54` | `GET` |
| 0c | `02` | name #2 `:path` |
| 0d-0e | `00 0b` | 11 bytes |
| 0f-19 | `2f 69 ... 6c` | `/index.html` |
| 1a | `04` | name #4 `host` |
| 1b-1c | `00 0e` | 14 bytes |
| 1d-2a | `6c 6f ... 30` | `localhost:9000` |
| 2b | `05` | name #5 `user-agent` |
| 2c-2d | `00 07` | 7 bytes |
| 2e-34 | `62 63 ... 31` | `bcurl/1` |
| 35 | `06` | name #6 `accept` |
| 36-37 | `00 03` | 3 bytes |
| 38-3a | `2a 2f 2a` | `*/*` |

## Response, frame 1: HEADERS (72 bytes)

```
< frame: length=66 type=1 flags=0
< 0000  00 00 00 42 01 00 03 00 03 32 30 30 07 00 09 74  ...B.....200...t
< 0010  65 78 74 2f 68 74 6d 6c 08 00 02 36 36 09 00 08  ext/html...66...
< 0020  62 73 65 72 76 65 2f 31 0a 00 1d 54 68 75 2c 20  bserve/1...Thu,
< 0030  30 31 20 4f 63 74 20 32 30 32 36 20 32 31 3a 33  01 Oct 2026 21:3
< 0040  38 3a 32 31 20 47 4d 54                          8:21 GMT
```

| Offset | Bytes | Meaning |
|---|---|---|
| 00-03 | `00 00 00 42` | Length = 0x42 = 66 bytes of payload |
| 04 | `01` | Type = HEADERS |
| 05 | `00` | Flags = 0, not the end: a DATA frame follows |
| 06 | `03` | name #3 `:status` |
| 07-08 | `00 03` | 3 bytes |
| 09-0b | `32 30 30` | `200` |
| 0c | `07` | name #7 `content-type` |
| 0d-0e | `00 09` | 9 bytes |
| 0f-17 | `74 65 ... 6c` | `text/html` |
| 18 | `08` | name #8 `content-length` |
| 19-1a | `00 02` | 2 bytes |
| 1b-1c | `36 36` | `66` |
| 1d | `09` | name #9 `server` |
| 1e-1f | `00 08` | 8 bytes |
| 20-27 | `62 73 ... 31` | `bserve/1` |
| 28 | `0a` | name #10 `date` |
| 29-2a | `00 1d` | 29 bytes |
| 2b-47 | `54 68 ... 54` | `Thu, 01 Oct 2026 21:38:21 GMT` |

## Response, frame 2: DATA (72 bytes)

```
< frame: length=66 type=0 flags=1
< 0000  00 00 00 42 00 01 3c 21 64 6f 63 74 79 70 65 20  ...B..<!doctype
< 0010  68 74 6d 6c 3e 0a 3c 74 69 74 6c 65 3e 62 73 65  html>.<title>bse
< 0020  72 76 65 3c 2f 74 69 74 6c 65 3e 0a 3c 68 31 3e  rve</title>.<h1>
< 0030  48 65 6c 6c 6f 20 66 72 6f 6d 20 42 48 54 54 50  Hello from BHTTP
< 0040  2f 31 3c 2f 68 31 3e 0a                          /1</h1>.
```

| Offset | Bytes | Meaning |
|---|---|---|
| 00-03 | `00 00 00 42` | Length = 66 bytes, same as `content-length` |
| 04 | `00` | Type = DATA |
| 05 | `01` | Flags = END, the response is complete |
| 06-47 | `3c 21 ... 0a` | the file `www/index.html`, byte for byte (`0a` = newline) |

The connection is still open after this frame. The client could send another
request on it. bcurl only has one URL, so it closes the connection.

Total: 59 bytes for the request and 144 for the response. 18 of those bytes
are frame headers (3 frames × 6 bytes).
