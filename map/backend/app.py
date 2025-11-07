# app.py
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/api/pings")
async def receive_ping(req: Request):
    data = await req.json()
    print("\n--- RECEIVED PING ---")
    print(data)  # plain print; use pprint if you want formatting
    return {"ok": True}
