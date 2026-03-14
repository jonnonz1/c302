"""Tests for the worm-bridge FastAPI server.

Validates the HTTP contract between the TypeScript agent and the Python
controller. Uses FastAPI's TestClient for synchronous in-process requests.
"""

from fastapi.testclient import TestClient

from worm_bridge.server import app

client = TestClient(app)

SIGNALS = {
    "error_count": 0,
    "test_pass_rate": 1.0,
    "files_changed": 0,
    "iterations": 0,
}


def test_health():
    """Verify /health returns server status, version, controller type, and uptime."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert body["controller_type"] == "static"
    assert "uptime_seconds" in body


def test_tick_returns_surface_and_state():
    """Verify /tick returns a TickResponse with valid surface parameters and state."""
    client.post("/reset")
    payload = {
        "reward": 0.5,
        "signals": {
            "error_count": 2,
            "test_pass_rate": 0.75,
            "files_changed": 1,
            "iterations": 3,
            "last_action_type": "read_file",
        },
    }
    response = client.post("/tick", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "surface" in body
    assert "state" in body
    surface = body["surface"]
    assert surface["mode"] == "diagnose"
    assert 0.2 <= surface["temperature"] <= 0.8
    assert 500 <= surface["token_budget"] <= 4000
    assert 1 <= surface["search_breadth"] <= 10
    assert 0.0 <= surface["aggression"] <= 1.0
    assert 0.3 <= surface["stop_threshold"] <= 0.8
    assert isinstance(surface["allowed_tools"], list)


def test_tick_null_reward():
    """Verify /tick accepts null reward for the first tick of an experiment."""
    client.post("/reset")
    payload = {
        "reward": None,
        "signals": SIGNALS,
    }
    response = client.post("/tick", json=payload)
    assert response.status_code == 200


def test_tick_cycles_modes():
    """Verify the static controller cycles through diagnose -> search -> edit-small -> run-tests."""
    client.post("/reset")
    expected_modes = ["diagnose", "search", "edit-small", "run-tests"]
    for expected_mode in expected_modes:
        response = client.post("/tick", json={"signals": SIGNALS})
        body = response.json()
        assert body["surface"]["mode"] == expected_mode


def test_state_returns_worm_state():
    """Verify /state returns all 6 controller internal variables."""
    response = client.get("/state")
    assert response.status_code == 200
    body = response.json()
    for key in ("arousal", "novelty_seek", "stability", "persistence", "error_aversion", "reward_trace"):
        assert key in body


def test_reset_clears_state():
    """Verify /reset returns confirmation and resets to initial state."""
    client.post("/tick", json={"signals": SIGNALS})
    response = client.post("/reset")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "reset"
    assert body["controller_type"] == "static"


def test_reset_restarts_mode_cycle():
    """Verify /reset restarts the mode cycle from diagnose."""
    client.post("/reset")
    client.post("/tick", json={"signals": SIGNALS})
    client.post("/tick", json={"signals": SIGNALS})
    client.post("/reset")
    response = client.post("/tick", json={"signals": SIGNALS})
    assert response.json()["surface"]["mode"] == "diagnose"


def test_config_returns_controller_config():
    """Verify /config returns controller configuration."""
    response = client.get("/config")
    assert response.status_code == 200
    body = response.json()
    assert body["controller_type"] == "static"
    assert "tool_masks" in body
    assert "diagnose" in body["tool_masks"]
    assert "stop" in body["tool_masks"]


def test_tick_tool_masks_match_mode():
    """Verify diagnose mode's allowed_tools matches the TOOL_MASKS definition."""
    client.post("/reset")
    response = client.post("/tick", json={"signals": SIGNALS})
    surface = response.json()["surface"]
    assert surface["mode"] == "diagnose"
    assert set(surface["allowed_tools"]) == {"read_file", "search_code", "list_files"}
