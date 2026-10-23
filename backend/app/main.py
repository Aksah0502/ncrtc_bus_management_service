from fastapi import FastAPI

from app.modules.auth.router import router as auth_router
from app.modules.fleet.router import router as fleet_router


app = FastAPI(
    title="NCRTC Bus Management System API",
    description="Backend APIs for bus operations, scheduling, tracking, incidents, and notices.",
    version="1.0.0",
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


@app.get("/health", tags=["Health"])
def health_check():
    """Check whether the API application is running."""
    return {"status": "ok"}