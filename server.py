from flask import Flask; app = Flask(__name__)
"""Room-code relay server. Run on any PC/VPS:  python server.py  (port 8765).
Phones/PCs connect with the room code and see each other live (up to 8 per room)."""
import asyncio, json, random
rooms = {}  # code -> {player_id: writer}
async def send_all(code, data, skip=None):
    for pid, w in list(rooms.get(code, {}).items()):
        if pid != skip:
            try:
                w.write(data)
            except Exception:
                pass


async def handle(r, w):
    pid, code = random.randrange(1 << 30), None
    try:
        while True:
            line = await asyncio.wait_for(r.readline(), timeout=30)
            if not line:
                break
            m = json.loads(line)
            if m.get("t") == "join" and code is None:
                c = str(m.get("code", ""))[:12]
                if len(rooms.get(c, {})) >= 8:
                    w.write(b'{"t":"full"}\n')
                    break
                code = c
                rooms.setdefault(code, {})[pid] = w
                w.write((json.dumps({"t": "ok", "id": pid}) + "\n").encode())
            elif m.get("t") == "s" and code:
                m["id"] = pid
                await send_all(code, (json.dumps(m) + "\n").encode(), skip=pid)
    except Exception:
        pass
    finally:
        if code and pid in rooms.get(code, {}):
            del rooms[code][pid]
            await send_all(code, (json.dumps({"t": "l", "id": pid}) + "\n").encode())
            if not rooms[code]:
                del rooms[code]
        try:
            w.close()
        except Exception:
            pass


async def main():
    srv = await asyncio.start_server(handle, "0.0.0.0", 8765, limit=1 << 16)
    print("Pot Climb server listening on port 8765")
    async with srv:
        await srv.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
