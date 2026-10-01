# Spec: HTTP in binary

This page is all you need to write a client or a server that works with ours.
All numbers are big-endian (network byte order).

## 1. Connection

- The client opens **one** TCP connection and sends a request. The server sends back a response.
- The server **keeps the connection open** after every response, even after 400 or 404.
- The client never opens a second connection.

## 2. Frame header (6 bytes)

Everything sent is a **frame**. Every frame starts with the same 6 bytes:

```
+-------+-------+-------+-------+-------+-------+------------------+
|          Length (4 bytes)     | Type  | Flags |  Payload         |
|                               |  (1)  |  (1)  |  (Length bytes)  |
+-------+-------+-------+-------+-------+-------+------------------+
```

| Field | Size | Meaning |
|---|---|---|
| Length | 4 bytes | how many payload bytes come after the header |
| Type | 1 byte | `0` = DATA, `1` = HEADERS, anything else = unknown |
| Flags | 1 byte | `1` = END: this is the last frame of the message |

### Why these sizes? (HTTP/2 uses 24 / 8 / 8 / 31)

HTTP/2 sends many requests **at the same time** on one connection, with their
frames mixed together. So:

- every frame needs a **31-bit stream ID** to say which request it belongs to (1 more bit is reserved, making 4 bytes)
- frames are kept small (the length is **24 bits**, default limit 16 KB), so one big file can't block the other requests for long

We send **one request at a time**, so we don't need either of those:

- **No stream ID.** The response to the first request comes first, the second comes second, and so on, so the order already tells you which is which. This saves 4 bytes on every frame.
- **32-bit length.** Nothing else is waiting, so a whole file (up to 4 GB) can go in one DATA frame.
- **8-bit type, like HTTP/2.** We use 2 types, which leaves 254 free for a version 2.
- **8-bit flags, like HTTP/2.** We use 1 bit. The other 7 must be sent as 0.

Our header is 6 bytes, HTTP/2's is 9. The downside: a big file holds up the
next request on the same connection.

## 3. Frame types

- **HEADERS (1):** the payload is a header block (section 4). Every message starts with one.
- **DATA (0):** the payload is body bytes. If there are several DATA frames, join them in order.
- **Unknown type: a receiver that meets a frame type it does not know MUST skip it cleanly.** It reads `Length` bytes, throws them away, and goes on to the next frame. The flags of an unknown frame are ignored. This is what leaves room for a version 2: new frame types can be added and old programs will just skip them.

A message ends with the first HEADERS or DATA frame that has the END flag.

## 4. Header block

The header block is a list of entries, one after another, until the payload
ends. Each entry is:

```
Index (1 byte)  [NameLen (1 byte) + Name]   ValueLen (2 bytes) + Value
                 ^ only if Index is 0
```

- **Index 1-10:** a name from the table below. The name costs 1 byte.
- **Index 0:** any other name, sent as a 1-byte length and then the name.
- **Index 11-255:** not allowed. The block is malformed.
- The value always comes as a 2-byte length followed by the text. Numbers are sent as text too, for example `:status` = `"200"`.

| # | name | sent by | # | name | sent by |
|---|---|---|---|---|---|
| 1 | `:method` | client | 6 | `accept` | client |
| 2 | `:path` | client | 7 | `content-type` | server |
| 3 | `:status` | server | 8 | `content-length` | server |
| 4 | `host` | client | 9 | `server` | server |
| 5 | `user-agent` | client | 10 | `date` | server |

These are the ten names we actually send. This is the first two ideas of
HPACK (HTTP/2's header compression): a **static table** of numbered names,
and a **length prefix** for everything else. We left out HPACK's dynamic
table and Huffman coding.

## 5. Request and response

**Request:** one HEADERS frame with END. It must contain `:path`, which
starts with `/`.

**Response:** one HEADERS frame (with `:status`), then one DATA frame with
END that holds the body.

| Status | When |
|---|---|
| 200 | the file at `:path` exists inside the server's root folder. The body is the file. |
| 404 | the file is not there, or the path tries to leave the root folder (`/../x`) |
| 400 | the request is malformed: the header block is cut short, uses an index above 10, has no `:path`, or a DATA frame came before HEADERS |

Even for a bad request the server first reads every frame up to END, and only
then answers. Every frame says its own length, so the server always knows
where the next request starts. That is why it can keep the connection open
after a 400.

## 6. Client (bcurl)

- Sends `:method GET`, `:path`, `host`, `user-agent` and `accept` in one HEADERS frame with END.
- Writes the response body to stdout.
- `-v` hexdumps every frame sent and received, on stderr.
- Exit code: 1 if the status is 4xx or 5xx, otherwise 0.

See `HEXDUMP.md` for one full request and response, explained byte by byte.
