from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import UTC, datetime
import json
import os
from typing import Any

from fastapi import WebSocket

from app.domain.models import AuthUser, UserRole


EVENT_STREAM = "ner:operations:events"
EVENT_CHANNEL = "ner:operations:live"


def redis_connection_settings() -> dict[str, Any]:
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return {"url": redis_url}
    redis_host = os.getenv("REDIS_HOST")
    if redis_host:
        return {
            "host": redis_host,
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "password": os.getenv("REDIS_PASSWORD") or None,
            "db": int(os.getenv("REDIS_DB", "0")),
        }
    return {}


class OperationsHub:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, AuthUser] = {}
        self._redis: Any = None
        self._pubsub: Any = None
        self._listener_task: asyncio.Task | None = None
        self.mode = "IN_MEMORY"

    async def start(self) -> None:
        settings = redis_connection_settings()
        if not settings:
            return
        try:
            from redis.asyncio import Redis

            self._redis = Redis.from_url(settings["url"], decode_responses=True) if "url" in settings else Redis(**settings, decode_responses=True)
            await self._redis.ping()
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe(EVENT_CHANNEL)
            self._listener_task = asyncio.create_task(self._listen(), name="redis-operations-listener")
            self.mode = "REDIS_STREAM"
        except Exception:
            self._redis = None
            self._pubsub = None
            self.mode = "IN_MEMORY_FALLBACK"

    async def stop(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listener_task
        if self._pubsub:
            await self._pubsub.aclose()
        if self._redis:
            await self._redis.aclose()
        self._listener_task = None
        self._pubsub = None
        self._redis = None

    async def _listen(self) -> None:
        async for message in self._pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                event = json.loads(message["data"])
            except (TypeError, json.JSONDecodeError):
                continue
            await self._broadcast(event)

    async def connect(self, websocket: WebSocket, user: AuthUser) -> None:
        await websocket.accept()
        self._connections[websocket] = user
        await websocket.send_json({
            "type": "CONNECTED",
            "message": "Authenticated real-time operations stream connected.",
            "transport": self.mode,
            "occurred_at": datetime.now(UTC).isoformat(),
        })

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.pop(websocket, None)

    async def _broadcast(self, event: dict[str, Any]) -> None:
        district = event.get("district")
        disconnected: list[WebSocket] = []
        for websocket, user in list(self._connections.items()):
            if user.role == UserRole.DISTRICT_AUTHORITY and district and user.district and district.casefold() != user.district.casefold():
                continue
            try:
                await websocket.send_json(event)
            except Exception:
                disconnected.append(websocket)
        for websocket in disconnected:
            self.disconnect(websocket)

    async def publish(self, event_type: str, changed_entities: list[str], actor: str, district: str | None = None) -> None:
        event = {
            "type": event_type,
            "changed_entities": changed_entities,
            "actor": actor,
            "district": district,
            "occurred_at": datetime.now(UTC).isoformat(),
        }
        if self._redis:
            try:
                await self._redis.xadd(EVENT_STREAM, {"payload": json.dumps(event)}, maxlen=10_000, approximate=True)
                return
            except Exception:
                self.mode = "IN_MEMORY_FALLBACK"
        await self._broadcast(event)


operations_hub = OperationsHub()
