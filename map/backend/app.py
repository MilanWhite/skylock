import asyncio, json
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# --- SQLAlchemy (async) ---
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON  # stored as TEXT

DB_URL = "sqlite+aiosqlite:///./pings.db"

class Base(DeclarativeBase): pass

class Ping(Base):
    __tablename__ = "pings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    mode: Mapped[str] = mapped_column(String(8))            # "SOS" | "OK"
    pdop: Mapped[float] = mapped_column(Float)
    answers_json: Mapped[dict] = mapped_column(SQLITE_JSON)  # raw list of {q,a} as JSON text

    answers: Mapped[List["PingAnswer"]] = relationship(
        back_populates="ping", cascade="all, delete-orphan"
    )

Index("ix_pings_device_ts", Ping.device_id, Ping.ts)

class PingAnswer(Base):
    __tablename__ = "ping_answers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ping_id: Mapped[int] = mapped_column(ForeignKey("pings.id", ondelete="CASCADE"), index=True)
    q: Mapped[str] = mapped_column(String(64), index=True)
    a: Mapped[str] = mapped_column(String(64), index=True)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)  # future-proof

    ping: Mapped[Ping] = relationship(back_populates="answers")

engine = create_async_engine(DB_URL, echo=False, future=True)
Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# --- FastAPI ---
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

def parse_ts(ts_str: str) -> datetime:
    # Accept "....Z" or offset form
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    return datetime.fromisoformat(ts_str)

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[db] ready at ./pings.db")

@app.post("/api/pings")
async def receive_ping(req: Request):
    data = await req.json()
    print("\n--- RECEIVED PING ---", data)

    # Normalize answers to a list of {q,a}
    answers = data.get("answers") or []
    if not isinstance(answers, list):
        answers = []

    # Persist
    async with Session() as session:
        p = Ping(
            device_id=str(data.get("deviceId", "")),
            ts=parse_ts(str(data.get("ts"))),
            lat=float(data.get("lat")),
            lon=float(data.get("lon")),
            mode=str(data.get("mode", "")),
            pdop=float(data.get("pdop", 0)),
            answers_json=answers,
        )
        session.add(p)
        await session.flush()  # get p.id

        for item in answers:
            q = str(item.get("q", "")).strip()
            a = str(item.get("a", "")).strip()
            session.add(PingAnswer(ping_id=p.id, q=q, a=a))

        await session.commit()

    # Broadcast unchanged payload to clients
    await broadcast(data)
    return {"ok": True}

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    connections.add(ws)
    print(f"[ws] connected. total={len(connections)}")
    await ws.send_text('{"type":"hello"}')
    try:
        while True:
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        pass
    finally:
        connections.discard(ws)
        print(f"[ws] disconnected. total={len(connections)}")

# Optional: simple reads
@app.get("/api/pings/latest")
async def latest(limit: int = 50):
    async with Session() as session:
        rows = (await session.execute(
            # newest first
            Ping.__table__.select().order_by(Ping.ts.desc()).limit(limit)
        )).mappings().all()
        return [dict(r) for r in rows]

@app.get("/api/pings/by_device/{device_id}")
async def by_device(device_id: str, limit: int = 100):
    async with Session() as session:
        rows = (await session.execute(
            Ping.__table__.select()
            .where(Ping.device_id == device_id)
            .order_by(Ping.ts.desc())
            .limit(limit)
        )).mappings().all()
        return [dict(r) for r in rows]
