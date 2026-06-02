import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from pythonjsonlogger import jsonlogger


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s',
        rename_fields={'asctime': 'timestamp', 'levelname': 'level', 'name': 'service'},
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


setup_logging()

from fastapi import FastAPI
from api.health import router as health_router
from api.internal import router as internal_router
from db.database import init_db

init_db()

app = FastAPI(title="ASim Simulation Engine", version="0.1.0")
app.include_router(health_router)
app.include_router(internal_router)
