"""Scientific analysis functions for c302 experiment traces.

Pure functions that read JSON trace files from an experiment directory
and compute metrics for understanding controller behavior.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def load_traces(experiment_dir: str | Path) -> dict[str, Any]:
    """Load all trace files from an experiment directory."""
    d = Path(experiment_dir)
    traces: dict[str, Any] = {}
    for name in [
        "control-surface-traces",
        "reward-history",
        "agent-actions",
        "repo-snapshots",
        "controller-state-traces",
    ]:
        path = d / f"{name}.json"
        if path.exists():
            traces[name] = json.loads(path.read_text())
    meta_path = d / "meta.json"
    if meta_path.exists():
        traces["meta"] = json.loads(meta_path.read_text())
    summary_path = d / "summary.json"
    if summary_path.exists():
        traces["summary"] = json.loads(summary_path.read_text())
    return traces


def mode_transition_matrix(surfaces: list[dict]) -> dict[str, dict[str, dict[str, Any]]]:
    """Compute mode-to-mode transition counts and average reward per transition."""
    matrix: dict[str, dict[str, list[float]]] = {}

    for i in range(1, len(surfaces)):
        prev_mode = surfaces[i - 1]["mode"]
        curr_mode = surfaces[i]["mode"]
        matrix.setdefault(prev_mode, {}).setdefault(curr_mode, [])

    return {
        from_mode: {
            to_mode: {"count": 0, "avg_reward": 0.0}
            for to_mode in to_modes
        }
        for from_mode, to_modes in matrix.items()
    }


def mode_transition_matrix_with_rewards(
    surfaces: list[dict], rewards: list[dict]
) -> dict[str, dict[str, dict[str, Any]]]:
    """Compute mode transition matrix with reward statistics."""
    matrix: dict[str, dict[str, list[float]]] = {}

    for i in range(1, len(surfaces)):
        prev_mode = surfaces[i - 1]["mode"]
        curr_mode = surfaces[i]["mode"]
        reward = rewards[i]["total"] if i < len(rewards) else 0.0
        matrix.setdefault(prev_mode, {}).setdefault(curr_mode, []).append(reward)

    return {
        from_mode: {
            to_mode: {
                "count": len(rews),
                "avg_reward": sum(rews) / len(rews) if rews else 0.0,
            }
            for to_mode, rews in to_modes.items()
        }
        for from_mode, to_modes in matrix.items()
    }


def tool_roi(actions: list[dict], snapshots: list[dict]) -> dict[str, dict[str, Any]]:
    """Compute ROI per tool: usage count and average test delta."""
    roi: dict[str, list[float]] = {}

    for i, action in enumerate(actions):
        if i + 1 >= len(snapshots):
            break
        before_rate = snapshots[i].get("test_results", {}).get("pass_rate", 0) if snapshots[i].get("test_results") else 0
        after_rate = snapshots[i + 1].get("test_results", {}).get("pass_rate", 0) if i + 1 < len(snapshots) and snapshots[i + 1].get("test_results") else 0
        delta = after_rate - before_rate

        for tc in action.get("tool_calls", []):
            tool = tc["tool"]
            roi.setdefault(tool, []).append(delta)

    return {
        tool: {
            "count": len(deltas),
            "avg_test_delta": sum(deltas) / len(deltas) if deltas else 0.0,
            "positive_pct": sum(1 for d in deltas if d > 0) / len(deltas) if deltas else 0.0,
        }
        for tool, deltas in roi.items()
    }


def token_efficiency(surfaces: list[dict], rewards: list[dict]) -> dict[str, Any]:
    """Compute tokens spent vs cumulative reward improvement."""
    total_tokens = sum(s.get("token_budget", 0) for s in surfaces)
    cumulative_reward = sum(r["total"] for r in rewards)
    positive_ticks = sum(1 for r in rewards if r["total"] > 0)

    return {
        "total_token_budget": total_tokens,
        "cumulative_reward": round(cumulative_reward, 4),
        "reward_per_1k_tokens": round(cumulative_reward / (total_tokens / 1000), 4) if total_tokens > 0 else 0.0,
        "positive_tick_pct": round(positive_ticks / len(rewards), 4) if rewards else 0.0,
    }


def reward_component_analysis(rewards: list[dict]) -> dict[str, dict[str, float]]:
    """Analyze each reward component: mean, variance, correlation with total."""
    if not rewards:
        return {}

    components = ["test_delta", "build_penalty", "lint_penalty", "patch_size_penalty", "progress_bonus"]
    result: dict[str, dict[str, float]] = {}

    totals = [r["total"] for r in rewards]
    total_mean = sum(totals) / len(totals)

    for comp in components:
        values = [r["components"][comp] for r in rewards]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        cov = sum((v - mean) * (t - total_mean) for v, t in zip(values, totals)) / len(values)
        total_var = sum((t - total_mean) ** 2 for t in totals) / len(totals)
        correlation = cov / math.sqrt(variance * total_var) if variance > 0 and total_var > 0 else 0.0

        result[comp] = {
            "mean": round(mean, 4),
            "variance": round(variance, 4),
            "correlation_with_total": round(correlation, 4),
        }

    return result


def state_trajectory(states: list[dict]) -> dict[str, dict[str, Any]]:
    """Compute velocity and acceleration of the 6 state variables."""
    vars_ = ["arousal", "novelty_seek", "stability", "persistence", "error_aversion", "reward_trace"]
    result: dict[str, dict[str, Any]] = {}

    for var in vars_:
        values = [s[var] for s in states]
        velocities = [values[i] - values[i - 1] for i in range(1, len(values))]
        accelerations = [velocities[i] - velocities[i - 1] for i in range(1, len(velocities))]

        result[var] = {
            "final": round(values[-1], 4) if values else 0.0,
            "mean_velocity": round(sum(velocities) / len(velocities), 4) if velocities else 0.0,
            "mean_acceleration": round(sum(accelerations) / len(accelerations), 4) if accelerations else 0.0,
            "range": [round(min(values), 4), round(max(values), 4)] if values else [0.0, 0.0],
        }

    return result


def convergence_profile(rewards: list[dict], snapshots: list[dict]) -> dict[str, Any]:
    """Measure how fast the controller reaches task completion."""
    pass_rates = []
    for s in snapshots:
        tr = s.get("test_results")
        pass_rates.append(tr["pass_rate"] if tr else 0.0)

    first_positive = None
    first_complete = None
    for i, r in enumerate(rewards):
        if first_positive is None and r["total"] > 0:
            first_positive = i
        if first_complete is None and i < len(pass_rates) and pass_rates[i] >= 1.0:
            first_complete = i

    return {
        "first_positive_reward_tick": first_positive,
        "first_complete_tick": first_complete,
        "total_ticks": len(rewards),
        "final_pass_rate": round(pass_rates[-1], 4) if pass_rates else 0.0,
    }


def behavioral_diversity(surfaces: list[dict]) -> dict[str, Any]:
    """Shannon entropy of mode distribution."""
    mode_counts: dict[str, int] = {}
    for s in surfaces:
        mode = s["mode"]
        mode_counts[mode] = mode_counts.get(mode, 0) + 1

    total = sum(mode_counts.values())
    if total == 0:
        return {"entropy": 0.0, "mode_counts": {}, "unique_modes": 0}

    entropy = 0.0
    for count in mode_counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)

    max_entropy = math.log2(7)

    return {
        "entropy": round(entropy, 4),
        "normalized_entropy": round(entropy / max_entropy, 4) if max_entropy > 0 else 0.0,
        "mode_counts": mode_counts,
        "unique_modes": len(mode_counts),
    }


def critical_moments(rewards: list[dict], surfaces: list[dict], actions: list[dict]) -> list[dict[str, Any]]:
    """Find ticks with large reward jumps and context."""
    if len(rewards) < 2:
        return []

    moments = []
    for i in range(1, len(rewards)):
        prev_total = rewards[i - 1]["total"]
        curr_total = rewards[i]["total"]
        delta = curr_total - prev_total

        if abs(delta) >= 0.1:
            moment: dict[str, Any] = {
                "tick": i,
                "reward_delta": round(delta, 4),
                "reward_before": round(prev_total, 4),
                "reward_after": round(curr_total, 4),
                "mode": surfaces[i]["mode"] if i < len(surfaces) else None,
                "mode_before": surfaces[i - 1]["mode"] if i - 1 < len(surfaces) else None,
            }
            if i < len(actions):
                moment["description"] = actions[i].get("description", "")[:200]
                moment["tools_used"] = [tc["tool"] for tc in actions[i].get("tool_calls", [])]
            moments.append(moment)

    moments.sort(key=lambda m: abs(m["reward_delta"]), reverse=True)
    return moments[:10]


def analyze(experiment_dir: str | Path) -> dict[str, Any]:
    """Run all analyses on an experiment directory and return combined results."""
    traces = load_traces(experiment_dir)

    surfaces = traces.get("control-surface-traces", [])
    rewards = traces.get("reward-history", [])
    actions = traces.get("agent-actions", [])
    snapshots = traces.get("repo-snapshots", [])
    states = traces.get("controller-state-traces", [])

    return {
        "experiment_dir": str(experiment_dir),
        "meta": traces.get("meta"),
        "mode_transitions": mode_transition_matrix_with_rewards(surfaces, rewards),
        "tool_roi": tool_roi(actions, snapshots),
        "token_efficiency": token_efficiency(surfaces, rewards),
        "reward_components": reward_component_analysis(rewards),
        "state_trajectory": state_trajectory(states),
        "convergence": convergence_profile(rewards, snapshots),
        "behavioral_diversity": behavioral_diversity(surfaces),
        "critical_moments": critical_moments(rewards, surfaces, actions),
    }
