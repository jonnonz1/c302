#!/usr/bin/env python3
"""Simulated Neural Activity Heatmap.

Simulates 30 ticks of the c302 network with a realistic scenario:
- Ticks 1-8: Tests failing (test_pass_rate=0.0), errors present
- Ticks 9-15: Partial fix (test_pass_rate=0.5), fewer errors
- Ticks 16-22: Tests passing (test_pass_rate=1.0), positive reward
- Ticks 23-30: Stable success, winding down

Uses the actual NEURON simulation via the live controller. If NEURON is not
available, falls back to a biologically-plausible synthetic trace.
"""

import sys
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

NEURON_NAMES = [
    "ASEL", "ASER", "AWCL", "AWCR",
    "AVAL", "AVAR", "AVBL", "AVBR",
    "AVDL", "AVDR", "AVEL", "AVER",
    "PVCL", "PVCR",
]

NUM_TICKS = 30

# ---------- Try live simulation ----------

def run_live_simulation():
    """Run the actual NEURON simulation."""
    sys.path.insert(0, "/Users/jonno/workspace/c302/worm-bridge")
    os.chdir("/Users/jonno/workspace/c302/worm-bridge")

    from worm_bridge.controllers import create_controller
    from worm_bridge.types import TickRequest, TickSignals

    controller = create_controller("live")

    activities = []  # list of dicts, one per tick
    modes = []

    scenarios = (
        # (ticks, test_pass_rate, error_count, reward)
        (8,  0.0, 5, -0.5),   # Failing tests, errors
        (7,  0.5, 2, 0.0),    # Partial fix
        (7,  1.0, 0, 0.8),    # Tests passing, reward
        (8,  1.0, 0, 0.3),    # Stable success
    )

    tick = 0
    for n_ticks, tpr, ec, rew in scenarios:
        for i in range(n_ticks):
            req = TickRequest(
                reward=rew if tick > 0 else None,
                signals=TickSignals(
                    error_count=ec,
                    test_pass_rate=tpr,
                    files_changed=1 if tpr < 1.0 else 0,
                    iterations=tick,
                ),
            )
            surface, state = controller.tick(req)
            act = controller.neuron_activity()
            tick_activities = {}
            if act:
                tick_activities.update(act.sensory)
                tick_activities.update(act.command)
            activities.append(tick_activities)
            modes.append(surface.mode.value)
            tick += 1

    return activities, modes


def generate_synthetic_trace():
    """Generate biologically plausible synthetic data as fallback."""
    activities = []
    modes = []

    mode_sequence = (
        ["diagnose"] * 3 + ["search"] * 2 + ["run-tests"] * 3 +
        ["diagnose"] * 2 + ["edit-small"] * 3 + ["run-tests"] * 2 +
        ["edit-small"] * 3 + ["run-tests"] * 2 +
        ["edit-small"] * 2 + ["run-tests"] * 2 + ["diagnose"] * 2 +
        ["stop"] * 4
    )

    np.random.seed(42)

    for tick in range(NUM_TICKS):
        t = tick / NUM_TICKS
        act = {}

        # Sensory: ASEL responds to positive signals (ramps up late)
        act["ASEL"] = 0.1 + 0.7 * max(0, (t - 0.5) * 2) + np.random.normal(0, 0.02)
        # ASER responds to negative signals (high early, drops)
        act["ASER"] = 0.6 * max(0, 1.0 - t * 1.5) + np.random.normal(0, 0.02)
        # AWC chemosensory: moderate throughout
        act["AWCL"] = 0.3 + 0.2 * math.sin(t * math.pi * 3) + np.random.normal(0, 0.02)
        act["AWCR"] = 0.25 + 0.15 * math.sin(t * math.pi * 3 + 0.5) + np.random.normal(0, 0.02)

        # Command interneurons: AVA high during errors, drops after fix
        ava_base = 0.7 * max(0, 1.0 - t * 2.0)
        act["AVAL"] = ava_base + 0.15 + np.random.normal(0, 0.03)
        act["AVAR"] = ava_base + 0.12 + np.random.normal(0, 0.03)

        # AVB: forward command, ramps up as tests pass
        avb_base = 0.2 + 0.5 * max(0, (t - 0.3))
        act["AVBL"] = avb_base + np.random.normal(0, 0.02)
        act["AVBR"] = avb_base + np.random.normal(0, 0.02)

        # AVD: driven by AVA feedback
        act["AVDL"] = ava_base * 0.8 + 0.1 + np.random.normal(0, 0.02)
        act["AVDR"] = ava_base * 0.75 + 0.1 + np.random.normal(0, 0.02)

        # AVE: moderate, tracks errors
        act["AVEL"] = 0.3 + 0.3 * max(0, 1.0 - t * 1.8) + np.random.normal(0, 0.02)
        act["AVER"] = 0.28 + 0.28 * max(0, 1.0 - t * 1.8) + np.random.normal(0, 0.02)

        # PVC: forward locomotion, high when tests failing (drives exploration)
        pvc_base = 0.6 * max(0, 1.0 - t * 1.2) + 0.1
        act["PVCL"] = pvc_base + np.random.normal(0, 0.03)
        act["PVCR"] = pvc_base + np.random.normal(0, 0.03)

        # Clamp all to [0, 1]
        for k in act:
            act[k] = max(0.0, min(1.0, act[k]))

        activities.append(act)
        modes.append(mode_sequence[tick] if tick < len(mode_sequence) else "stop")

    return activities, modes


# ---------- Run simulation ----------

try:
    print("Attempting live NEURON simulation...")
    activities, modes = run_live_simulation()
    sim_label = "Live NEURON Simulation"
    print(f"Live simulation complete: {len(activities)} ticks")
except Exception as e:
    print(f"Live simulation failed ({e}), using synthetic trace")
    activities, modes = generate_synthetic_trace()
    sim_label = "Synthetic Trace (NEURON unavailable)"


# ---------- Build heatmap matrix ----------

matrix = np.zeros((len(NEURON_NAMES), NUM_TICKS))
for t, act in enumerate(activities[:NUM_TICKS]):
    for i, name in enumerate(NEURON_NAMES):
        matrix[i, t] = act.get(name, 0.0)


# ---------- Plot ----------

fig, ax = plt.subplots(figsize=(16, 7))
fig.patch.set_facecolor("#0F172A")
ax.set_facecolor("#0F172A")

# Custom colormap: dark blue -> cyan -> yellow -> red
colors_list = ["#0F172A", "#1E3A5F", "#0EA5E9", "#22D3EE", "#FDE047", "#F97316", "#EF4444"]
cmap = mcolors.LinearSegmentedColormap.from_list("neural", colors_list, N=256)

im = ax.imshow(matrix, aspect="auto", cmap=cmap, interpolation="bilinear",
               vmin=0, vmax=1.0)

# Y-axis: neuron names with color coding
ax.set_yticks(range(len(NEURON_NAMES)))
ax.set_yticklabels(NEURON_NAMES, fontsize=9, fontfamily="monospace")

# Color the y-tick labels
sensory = {"ASEL", "ASER", "AWCL", "AWCR"}
command = {"AVAL", "AVAR", "AVBL", "AVBR", "AVDL", "AVDR", "AVEL", "AVER"}
forward = {"PVCL", "PVCR"}
for i, label in enumerate(ax.get_yticklabels()):
    name = NEURON_NAMES[i]
    if name in sensory:
        label.set_color("#60A5FA")
    elif name in command:
        label.set_color("#F87171")
    else:
        label.set_color("#4ADE80")

# X-axis: tick numbers
ax.set_xticks(range(NUM_TICKS))
ax.set_xticklabels([str(i + 1) for i in range(NUM_TICKS)], fontsize=7, color="#94A3B8")
ax.set_xlabel("Tick", fontsize=12, color="#CBD5E1", labelpad=8)

# Mode labels on top
ax2 = ax.twiny()
ax2.set_xlim(ax.get_xlim())
ax2.set_xticks(range(NUM_TICKS))

# Abbreviate mode names
mode_abbrev = {
    "diagnose": "DX", "search": "SR", "edit-small": "ES",
    "edit-large": "EL", "run-tests": "RT", "reflect": "RF", "stop": "ST",
}
mode_colors = {
    "diagnose": "#60A5FA", "search": "#A78BFA", "edit-small": "#34D399",
    "edit-large": "#FBBF24", "run-tests": "#F87171", "reflect": "#FB923C",
    "stop": "#6B7280",
}

mode_labels = [mode_abbrev.get(m, m[:2].upper()) for m in modes[:NUM_TICKS]]
ax2.set_xticklabels(mode_labels, fontsize=7, fontfamily="monospace", rotation=0)
for i, label in enumerate(ax2.get_xticklabels()):
    label.set_color(mode_colors.get(modes[i], "#94A3B8"))
ax2.set_xlabel("Agent Mode", fontsize=12, color="#CBD5E1", labelpad=8)
ax2.tick_params(colors="#94A3B8")

# Colorbar
cbar = plt.colorbar(im, ax=ax, pad=0.02, fraction=0.03)
cbar.set_label("Neural Activity", fontsize=10, color="#CBD5E1")
cbar.ax.tick_params(colors="#94A3B8")

# Phase annotations
phase_boundaries = [
    (0, 7, "Tests Failing\nerrors + negative reward"),
    (8, 14, "Partial Fix\nmixed signals"),
    (15, 21, "Tests Passing\npositive reward"),
    (22, 29, "Stable\nwinding down"),
]

for start, end, label in phase_boundaries:
    mid = (start + end) / 2
    ax.axvline(x=start - 0.5, color="#475569", linewidth=0.5, linestyle="--", alpha=0.5)
    ax.text(mid, -1.8, label, ha="center", va="top", fontsize=7, color="#94A3B8",
            fontfamily="sans-serif")

# Functional group brackets
ax.text(-2.8, 1.5, "Sensory", ha="center", va="center", fontsize=9, color="#60A5FA",
        rotation=90, fontweight="bold")
ax.text(-2.8, 8, "Command\nInterneurons", ha="center", va="center", fontsize=9,
        color="#F87171", rotation=90, fontweight="bold")
ax.text(-2.8, 12.5, "PVC", ha="center", va="center", fontsize=9, color="#4ADE80",
        rotation=90, fontweight="bold")

# Horizontal separators between groups
ax.axhline(y=3.5, color="#475569", linewidth=1.0, linestyle="-", alpha=0.4)
ax.axhline(y=11.5, color="#475569", linewidth=1.0, linestyle="-", alpha=0.4)

# Title
fig.suptitle(f"c302 Neural Activity Over Time ({sim_label})",
             fontsize=16, fontweight="bold", color="white", y=0.98)

# Mode legend
mode_legend_text = "  ".join(f"{v}={k}" for k, v in mode_abbrev.items())
fig.text(0.5, 0.01, mode_legend_text, ha="center", fontsize=8, color="#64748B",
         fontfamily="monospace")

ax.tick_params(colors="#94A3B8")
for spine in ax.spines.values():
    spine.set_color("#334155")

plt.tight_layout(rect=[0.05, 0.04, 0.97, 0.95])

out = "/Users/jonno/workspace/c302/research/figures/02_activity_heatmap.png"
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"Saved: {out}")
