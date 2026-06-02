import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from api.health import router as health_router
from api.internal import router as internal_router
from db.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

init_db()

app = FastAPI(title="ASim Simulation Engine", version="0.1.0")
app.include_router(health_router)
app.include_router(internal_router)
