"""
Tests for the worm-bridge FastAPI server.

Phase 0: Verifies all endpoint stubs return correct responses.
Covers health, tick, state, reset, and config endpoints.
"""

from fastapi.testclient import TestClient

from worm_bridge.server import app

client = TestClient(app)


def test_health():
    """Health endpoint returns status ok, version, and controller type."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert body["controller_type"] == "static"
    assert "uptime_seconds" in body


def test_tick_returns_surface_and_state():
    """Tick endpoint accepts a TickRequest and returns TickResponse."""
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
    """Tick endpoint accepts null reward (first tick of an experiment)."""
    client.post("/reset")
    payload = {
        "reward": None,
        "signals": {
            "error_count": 0,
            "test_pass_rate": 1.0,
            "files_changed": 0,
            "iterations": 0,
        },
    }
    response = client.post("/tick", json=payload)
    assert response.status_code == 200


def test_tick_cycles_modes():
    """Static controller cycles through the fixed mode sequence."""
    client.post("/reset")
    expected_modes = ["diagnose", "search", "edit-small", "run-tests"]
    signals = {
        "error_count": 0,
        "test_pass_rate": 1.0,
        "files_changed": 0,
        "iterations": 0,
    }
    for expected_mode in expected_modes:
        response = client.post("/tick", json={"signals": signals})
        body = response.json()
        assert body["surface"]["mode"] == expected_mode


def test_state_returns_worm_state():
    """State endpoint returns the current WormState."""
    response = client.get("/state")
    assert response.status_code == 200
    body = response.json()
    assert "arousal" in body
    assert "novelty_seek" in body
    assert "stability" in body
    assert "persistence" in body
    assert "error_aversion" in body
    assert "reward_trace" in body


def test_reset_clears_state():
    """Reset endpoint resets controller to initial state."""
    client.post("/tick", json={
        "signals": {
            "error_count": 0,
            "test_pass_rate": 1.0,
            "files_changed": 0,
            "iterations": 0,
        },
    })
    response = client.post("/reset")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "reset"
    assert body["controller_type"] == "static"


def test_reset_restarts_mode_cycle():
    """After reset, the mode cycle starts from the beginning."""
    client.post("/reset")
    signals = {
        "error_count": 0,
        "test_pass_rate": 1.0,
        "files_changed": 0,
        "iterations": 0,
    }
    client.post("/tick", json={"signals": signals})
    client.post("/tick", json={"signals": signals})
    client.post("/reset")
    response = client.post("/tick", json={"signals": signals})
    assert response.json()["surface"]["mode"] == "diagnose"


def test_config_returns_controller_config():
    """Config endpoint returns controller type, parameters, and tool masks."""
    response = client.get("/config")
    assert response.status_code == 200
    body = response.json()
    assert body["controller_type"] == "static"
    assert "mode_sequence" in body
    assert "fixed_parameters" in body
    assert "tool_masks" in body
    assert "diagnose" in body["tool_masks"]
    assert "stop" in body["tool_masks"]


def test_tick_tool_masks_match_mode():
    """Each mode's allowed_tools matches the documented tool mask."""
    client.post("/reset")
    signals = {
        "error_count": 0,
        "test_pass_rate": 1.0,
        "files_changed": 0,
        "iterations": 0,
    }
    response = client.post("/tick", json={"signals": signals})
    surface = response.json()["surface"]
    assert surface["mode"] == "diagnose"
    assert set(surface["allowed_tools"]) == {"read_file", "search", "list_files"}
