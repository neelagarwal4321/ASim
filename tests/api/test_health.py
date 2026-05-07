import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_200():
    r = client.get("/health")
    assert r.status_code == 200


def test_health_status_ok():
    r = client.get("/health")
    assert r.json().get("status") == "ok"
