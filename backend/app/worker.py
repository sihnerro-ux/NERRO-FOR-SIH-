from __future__ import annotations

import json
import os
import socket
import time

import httpx
from redis import Redis
from redis.exceptions import ResponseError

from app.realtime import EVENT_CHANNEL, EVENT_STREAM, redis_connection_settings


CONSUMER_GROUP = "ner-event-relays"
WORKER_STATUS_KEY = "ner:worker:intelligence-status"


def redis_client() -> Redis:
    settings = redis_connection_settings()
    if not settings:
        raise RuntimeError("REDIS_HOST or REDIS_URL is required for the worker")
    return Redis.from_url(settings["url"], decode_responses=True) if "url" in settings else Redis(**settings, decode_responses=True)


def run() -> None:
    client = redis_client()
    consumer = os.getenv("WORKER_NAME", socket.gethostname())
    while True:
        try:
            client.ping()
            try:
                client.xgroup_create(EVENT_STREAM, CONSUMER_GROUP, id="0", mkstream=True)
            except ResponseError as exc:
                if "BUSYGROUP" not in str(exc):
                    raise
            break
        except Exception:
            time.sleep(2)

    refresh_interval = max(60, int(os.getenv("WEATHER_REFRESH_INTERVAL_SECONDS", "900")))
    next_weather_refresh = time.monotonic() + max(5, int(os.getenv("WEATHER_INITIAL_DELAY_SECONDS", "20")))
    backend_url = os.getenv("BACKEND_INTERNAL_URL", "http://backend:8000")
    worker_token = os.getenv("WORKER_TOKEN", "")

    while True:
        messages = client.xreadgroup(CONSUMER_GROUP, consumer, {EVENT_STREAM: ">"}, count=20, block=5000)
        for _stream, entries in messages:
            for message_id, values in entries:
                payload = values.get("payload")
                if payload:
                    json.loads(payload)
                    client.publish(EVENT_CHANNEL, payload)
                client.xack(EVENT_STREAM, CONSUMER_GROUP, message_id)
        if time.monotonic() < next_weather_refresh:
            continue
        checked_at = time.time()
        try:
            response = httpx.post(
                f"{backend_url}/api/v1/internal/jobs/weather-intelligence",
                headers={"X-Worker-Token": worker_token},
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            client.hset(WORKER_STATUS_KEY, mapping={
                "status": result.get("status", "UNKNOWN"),
                "checked_at": checked_at,
                "changed_count": len(result.get("changed_entities", [])),
            })
            client.hdel(WORKER_STATUS_KEY, "error")
        except Exception as exc:
            client.hset(WORKER_STATUS_KEY, mapping={
                "status": "ERROR",
                "checked_at": checked_at,
                "error": str(exc)[:300],
            })
        next_weather_refresh = time.monotonic() + refresh_interval


if __name__ == "__main__":
    run()
