"""Direct unit tests for controller implementations (no HTTP)."""

import pytest

from worm_bridge.controllers import create_controller, RandomController, StaticController, SyntheticController
from worm_bridge.types import AgentMode, TickRequest, TickSignals, WormState


def _make_request(reward=None, error_count=0, test_pass_rate=1.0, files_changed=0, iterations=0):
    """Build a TickRequest with sensible defaults."""
    return TickRequest(
        reward=reward,
        signals=TickSignals(
            error_count=error_count,
            test_pass_rate=test_pass_rate,
            files_changed=files_changed,
            iterations=iterations,
        ),
    )


# --- Factory ---

class TestFactory:
    def test_create_static(self):
        """Factory creates a StaticController."""
        c = create_controller("static")
        assert isinstance(c, StaticController)
        assert c.controller_type == "static"

    def test_create_synthetic(self):
        """Factory creates a SyntheticController."""
        c = create_controller("synthetic")
        assert isinstance(c, SyntheticController)
        assert c.controller_type == "synthetic"

    def test_unknown_type_raises(self):
        """Factory raises ValueError for unknown type."""
        with pytest.raises(ValueError, match="Unknown controller type"):
            create_controller("nonexistent")


# --- StaticController ---

class TestStaticController:
    def test_cycles_modes(self):
        """Static controller cycles through fixed mode sequence."""
        c = StaticController()
        expected = ["diagnose", "search", "edit-small", "run-tests"]
        for mode_val in expected:
            surface, state = c.tick(_make_request())
            assert surface.mode.value == mode_val

    def test_wraps_around(self):
        """Mode cycle wraps after 4 ticks."""
        c = StaticController()
        for _ in range(4):
            c.tick(_make_request())
        surface, _ = c.tick(_make_request())
        assert surface.mode == AgentMode.DIAGNOSE

    def test_fixed_parameters(self):
        """Surface parameters are constant."""
        c = StaticController()
        surface, _ = c.tick(_make_request())
        assert surface.temperature == 0.5
        assert surface.token_budget == 2000
        assert surface.search_breadth == 3
        assert surface.aggression == 0.5
        assert surface.stop_threshold == 0.5

    def test_ignores_reward(self):
        """State does not change regardless of reward."""
        c = StaticController()
        initial = c.state().model_copy()
        c.tick(_make_request(reward=-1.0, error_count=10))
        assert c.state() == initial

    def test_reset(self):
        """Reset restores initial state and tick counter."""
        c = StaticController()
        c.tick(_make_request())
        c.tick(_make_request())
        c.reset()
        surface, _ = c.tick(_make_request())
        assert surface.mode == AgentMode.DIAGNOSE

    def test_neuron_activity_none(self):
        """Static controller returns no neuron activity."""
        c = StaticController()
        assert c.neuron_activity() is None


# --- SyntheticController ---

class TestSyntheticController:
    def test_state_changes_with_negative_reward(self):
        """State actually updates after tick with negative reward."""
        c = SyntheticController()
        initial = c.state().model_copy()
        c.tick(_make_request(reward=-0.5, error_count=5, test_pass_rate=0.3))
        updated = c.state()
        assert updated.reward_trace != initial.reward_trace
        assert updated.arousal != initial.arousal

    def test_reward_trace_ema(self):
        """Reward trace follows EMA with alpha=0.3."""
        c = SyntheticController()
        c.tick(_make_request(reward=1.0))
        assert abs(c.state().reward_trace - 0.3) < 0.01

        c.reset()
        c.tick(_make_request(reward=-1.0))
        assert abs(c.state().reward_trace - (-0.3)) < 0.01

    def test_arousal_from_signals(self):
        """Arousal blends signal-driven target with previous value."""
        c = SyntheticController()
        c.tick(_make_request(error_count=10, test_pass_rate=0.0))
        # target=0.8, blended from default 0.5: 0.4*0.5 + 0.6*0.8 = 0.68
        assert c.state().arousal > 0.5
        assert c.state().arousal < 0.8

        c.reset()
        c.tick(_make_request(error_count=0, test_pass_rate=1.0))
        # target=0.3, blended from default 0.5: 0.4*0.5 + 0.6*0.3 = 0.38
        assert c.state().arousal < 0.5
        assert c.state().arousal > 0.2

    def test_novelty_seek_increases_on_negative_reward(self):
        """Novelty seek increases when reward is negative."""
        c = SyntheticController()
        initial_ns = c.state().novelty_seek
        c.tick(_make_request(reward=-0.5))
        assert c.state().novelty_seek > initial_ns

    def test_novelty_seek_decreases_on_positive_reward(self):
        """Novelty seek decreases when reward is positive."""
        c = SyntheticController()
        initial_ns = c.state().novelty_seek
        c.tick(_make_request(reward=0.5))
        assert c.state().novelty_seek < initial_ns

    def test_error_aversion_spikes_on_bad_reward(self):
        """Error aversion increases on strongly negative reward."""
        c = SyntheticController()
        c.tick(_make_request(reward=-0.5))
        ea1 = c.state().error_aversion
        assert ea1 > 0.0

    def test_stability_inverse_of_arousal(self):
        """Stability is blended but inversely correlated with arousal."""
        c = SyntheticController()
        c.tick(_make_request(error_count=10, test_pass_rate=0.0))
        s = c.state()
        # High arousal should produce low stability (inverse relationship)
        assert s.arousal > 0.5
        assert s.stability < 0.6
        # After many ticks, stability converges toward 1 - 0.8 * arousal
        for _ in range(10):
            c.tick(_make_request(error_count=10, test_pass_rate=0.0))
        s2 = c.state()
        expected = max(0, 1.0 - s2.arousal * 0.8)
        assert s2.stability == pytest.approx(expected, abs=0.05)

    def test_mode_changes_based_on_state(self):
        """Mode is not a fixed cycle -- it depends on state."""
        c = SyntheticController()
        modes = set()
        for i in range(15):
            reward = -0.8 if i < 8 else 0.5
            error_count = 10 if i < 8 else 0
            surface, _ = c.tick(_make_request(
                reward=reward,
                error_count=error_count,
                test_pass_rate=0.2 if i < 8 else 0.9,
                iterations=i,
            ))
            modes.add(surface.mode.value)
        assert len(modes) >= 2

    def test_surface_derived_from_state(self):
        """Surface parameters vary based on state, not fixed."""
        c = SyntheticController()
        surfaces = []
        for i in range(5):
            surface, _ = c.tick(_make_request(
                reward=-0.8 if i < 3 else 0.5,
                error_count=10 if i < 3 else 0,
                test_pass_rate=0.1 if i < 3 else 0.9,
            ))
            surfaces.append(surface)
        temps = [s.temperature for s in surfaces]
        assert max(temps) != min(temps)

    def test_reset_clears_state(self):
        """Reset returns state to defaults."""
        c = SyntheticController()
        c.tick(_make_request(reward=-1.0, error_count=10, test_pass_rate=0.0))
        c.reset()
        default = WormState()
        assert c.state() == default

    def test_stop_mode_when_calm_and_stable(self):
        """Stop mode triggers when arousal low, stability high, reward_trace above threshold."""
        c = SyntheticController()
        c._state = WormState(
            arousal=0.1,
            novelty_seek=0.3,
            stability=0.9,
            persistence=0.5,
            error_aversion=0.0,
            reward_trace=0.9,
        )
        mode = c._derive_mode()
        assert mode == AgentMode.STOP

    def test_run_tests_on_high_error_aversion(self):
        """Run-tests mode when error_aversion high and reward_trace negative."""
        c = SyntheticController()
        c._state = WormState(
            arousal=0.5,
            novelty_seek=0.3,
            stability=0.5,
            persistence=0.5,
            error_aversion=0.8,
            reward_trace=-0.2,
        )
        mode = c._derive_mode()
        assert mode == AgentMode.RUN_TESTS

    def test_search_on_high_novelty_low_stability(self):
        """Search mode when novelty_seek high and stability low."""
        c = SyntheticController()
        c._state = WormState(
            arousal=0.5,
            novelty_seek=0.8,
            stability=0.3,
            persistence=0.5,
            error_aversion=0.2,
            reward_trace=0.1,
        )
        mode = c._derive_mode()
        assert mode == AgentMode.SEARCH

    def test_neuron_activity_none(self):
        """Synthetic controller returns no neuron activity."""
        c = SyntheticController()
        assert c.neuron_activity() is None

    def test_surface_temperature_range(self):
        """Temperature stays within [0.2, 0.8]."""
        c = SyntheticController()
        for ns in [0.0, 0.5, 1.0]:
            c._state = WormState(novelty_seek=ns)
            surface = c._derive_surface(AgentMode.DIAGNOSE)
            assert 0.2 <= surface.temperature <= 0.8

    def test_surface_token_budget_range(self):
        """Token budget stays within [500, 4000]."""
        c = SyntheticController()
        for p in [0.0, 0.5, 1.0]:
            c._state = WormState(persistence=p)
            surface = c._derive_surface(AgentMode.DIAGNOSE)
            assert 500 <= surface.token_budget <= 4000


# --- RandomController ---

class TestRandomController:
    def test_produces_valid_surface(self):
        """All surface parameters are within valid ranges."""
        c = RandomController(seed=42)
        for _ in range(20):
            surface, state = c.tick(_make_request())
            assert 0.2 <= surface.temperature <= 0.8
            assert 500 <= surface.token_budget <= 4000
            assert 1 <= surface.search_breadth <= 10
            assert 0.0 <= surface.aggression <= 1.0
            assert 0.3 <= surface.stop_threshold <= 0.8
            assert len(surface.allowed_tools) >= 0
            assert 0.0 <= state.arousal <= 1.0
            assert 0.0 <= state.novelty_seek <= 1.0
            assert 0.0 <= state.stability <= 1.0
            assert 0.0 <= state.persistence <= 1.0
            assert 0.0 <= state.error_aversion <= 1.0
            assert -1.0 <= state.reward_trace <= 1.0

    def test_mode_varies(self):
        """Running 20 ticks produces at least 2 different modes."""
        c = RandomController(seed=42)
        modes = set()
        for _ in range(20):
            surface, _ = c.tick(_make_request())
            modes.add(surface.mode)
        assert len(modes) >= 2

    def test_never_stops(self):
        """Random controller never selects STOP mode."""
        c = RandomController(seed=42)
        for _ in range(100):
            surface, _ = c.tick(_make_request())
            assert surface.mode != AgentMode.STOP

    def test_reset(self):
        """Reset restores state to defaults."""
        c = RandomController(seed=42)
        c.tick(_make_request())
        c.reset()
        assert c.state() == WormState()

    def test_seeded_reproducibility(self):
        """Same seed produces identical sequences."""
        a = RandomController(seed=123)
        b = RandomController(seed=123)
        for _ in range(10):
            req = _make_request()
            sa, wa = a.tick(req)
            sb, wb = b.tick(req)
            assert sa.mode == sb.mode
            assert sa.temperature == sb.temperature
            assert sa.token_budget == sb.token_budget
            assert wa == wb

    def test_factory_creates(self):
        """create_controller('random') returns a RandomController."""
        c = create_controller("random")
        assert isinstance(c, RandomController)
        assert c.controller_type == "random"
