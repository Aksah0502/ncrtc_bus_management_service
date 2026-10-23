from fastapi import FastAPI

from app.modules.auth.router import router as auth_router
from app.modules.fleet.router import router as fleet_router
from app.modules.routes.router import router as routes_router
from app.modules.scheduling.router import (router as scheduling_router, duties_router,)
from app.modules.avls.router import router as avls_router
import os
from contextlib import asynccontextmanager
from threading import Event, Thread

@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = Event()
    simulator_thread = None

    enabled = os.getenv(
        "GPS_SIMULATOR_ENABLED", "false"
    ).strip().lower() in {"1", "true", "yes", "on"}

    if enabled:
        from scripts.gps_tick import run_simulator

        simulator_thread = Thread(
            target=run_simulator,
            args=(stop_event, 5.0),
            name="gps-simulator",
            daemon=True,
        )
        simulator_thread.start()
        print("GPS simulator started automatically.", flush=True)

    try:
        yield
    finally:
        if simulator_thread is not None:
            stop_event.set()
            simulator_thread.join(timeout=10)
            print("GPS simulator stopped.", flush=True)

app = FastAPI(
    title="NCRTC Bus Management System API",
    description="Backend APIs for bus operations, scheduling, tracking, incidents, and notices.",
    version="1.0.0",
    lifespan=lifespan,
)


# Register authentication endpoints under /api/v1
app.include_router(
    auth_router,
    prefix="/api/v1",
)

app.include_router(
    fleet_router, 
    prefix="/api/v1"
)

app.include_router(
    routes_router,
    prefix="/api/v1"
)


app.include_router(
    scheduling_router,
    prefix="/api/v1"
)

app.include_router(
    duties_router,
    prefix="/api/v1"
)

app.include_router(
    avls_router,
    prefix="/api/v1"
)

@app.get("/health", tags=["Health"])
def health_check():
    """Check whether the API application is running."""
    return {"status": "ok"}