import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
SIM = "test-sim-001"


def test_start_returns_ok():
    with patch("tasks.simulation_tasks.run_full_simulation") as t:
        t.delay = MagicMock()
        r = client.post("/internal/simulate/start", json={
            "simulation_id": SIM, "scenario": "Test"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_status_returns_200():
    r = client.get(f"/internal/simulate/{SIM}/status")
    assert r.status_code == 200


def test_inject_event_ok():
    r = client.post(f"/internal/simulate/{SIM}/inject-event",
                    json={"simulation_id": SIM, "round_num": 1, "event_text": "Protest"})
    assert r.status_code == 200 and r.json()["ok"] is True


def test_control_pause():
    r = client.post(f"/internal/simulate/{SIM}/control", json={"action": "pause"})
    assert r.status_code == 200
