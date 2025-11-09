# app.py
import asyncio, json
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

connections: set[WebSocket] = set()

async def broadcast(payload: dict):
    dead = []
    for ws in connections:
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections.discard(ws)
    print(f"[broadcast] sent to {len(connections)} client(s)")

@app.post("/api/pings")
async def receive_ping(req: Request):
    data = await req.json()
    print("\n--- RECEIVED PING ---", data)
    await broadcast(data)
    return {"ok": True}

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    connections.add(ws)
    print(f"[ws] connected. total={len(connections)}")
    # immediate hello so you see a message in the browser console
    await ws.send_text('{"type":"hello"}')
    try:
        while True:
            await asyncio.sleep(60)  # keep alive; no need for client to send
    except WebSocketDisconnect:
        pass
    finally:
        connections.discard(ws)
        print(f"[ws] disconnected. total={len(connections)}")
