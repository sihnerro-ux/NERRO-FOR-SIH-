from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.auth.service import auth_service
from app.realtime import operations_hub


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await operations_hub.start()
    try:
        yield
    finally:
        await operations_hub.stop()

app = FastAPI(
    title="NER Logistics Control Tower API",
    version="0.2.0",
    description="Operational API for the PS26002 prototype.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "realtime": operations_hub.mode, "timestamp": datetime.now(UTC).isoformat()}


app.include_router(router, prefix="/api/v1")
auth_service.seed_demo_users()
