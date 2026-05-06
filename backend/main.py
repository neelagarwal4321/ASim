"""
backend/main.py — FastAPI application entry point.

Phase 1: Single health check endpoint only.
The CLI is the entry point for Phase 1 simulations.
Phase 2 will add internal simulation routes under /internal/*.
"""
import logging
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ASim Backend",
    description="Agent Society Simulator — simulation engine (internal only)",
    version="0.1.0-phase1",
)


@app.get("/health")
async def health_check() -> dict:
    """Liveness probe — returns status and current phase."""
    return {"status": "ok", "phase": 1}
