#!/usr/bin/env python3
"""
V5 Controller State Variable Traces — "The Feelings"

The 6 state variables (arousal, novelty_seek, stability, persistence,
error_aversion, reward_trace) plotted over ticks for a single LIVE L2 run.
Shows the agent's internal "feelings" evolving in response to actions.
"""

import json
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
import _font_setup  # noqa: F401 — registers Inter + JetBrains Mono
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe
import numpy as np
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

DARK_BG = "#0d1117"
TEXT_COLOR = "#c9d1d9"
SUBTLE_TEXT = "#8b949e"
GRID_COLOR = "#21262d"

# State variable colors
STATE_COLORS = {
    "arousal":        "#FF6B6B",  # coral red
    "novelty_seek":   "#4ECDC4",  # teal
    "stability":      "#45B7D1",  # sky blue
    "persistence":    "#96CEB4",  # sage
    "error_aversion": "#FFEAA7",  # gold
    "reward_trace":   "#DDA0DD",  # plum
}

STATE_LABELS = {
    "arousal":        "arousal",
    "novelty_seek":   "novelty seek",
    "stability":      "stability",
    "persistence":    "persistence",
    "error_aversion": "error aversion",
    "reward_trace":   "reward trace",
}

# Mode colors (from v1)
MODE_COLORS = {
    "reflect":    "#6C8EBF",
    "diagnose":   "#82B366",
    "search":     "#D6B656",
    "edit-small": "#E07C3E",
    "edit-large": "#CC4125",
    "run-tests":  "#9673A6",
    "stop":       "#B85450",
}

MODE_LABELS = {
    "reflect":    "reflect",
    "diagnose":   "diagnose",
    "search":     "search",
    "edit-small": "edit-sm",
    "edit-large": "edit-lg",
    "run-tests":  "test",
    "stop":       "stop",
}

DATA_DIR = Path("/Users/jonno/workspace/c302/research/experiments")
RUN_DIR = DATA_DIR / "live-battery-20260403-224824-01"
OUT_DIR = Path("/Users/jonno/workspace/c302/research/figures")

# ── Load data ─────────────────────────────────────────────────────────────────

with open(RUN_DIR / "controller-state-traces.json") as f:
    state_data = json.load(f)

with open(RUN_DIR / "reward-history.json") as f:
    reward_data = json.load(f)

with open(RUN_DIR / "control-surface-traces.json") as f:
    surface_data = json.load(f)

n_ticks = len(state_data)
ticks = np.arange(n_ticks)

# Extract state variables
variables = {}
for var_name in STATE_COLORS:
    variables[var_name] = [s[var_name] for s in state_data]

# Shift reward_trace into 0-1 range for display (raw values are ~-0.14 to +0.01)
# Map to 0-1 so it reads alongside the other variables
rt = variables["reward_trace"]
rt_min, rt_max = min(rt), max(rt)
margin = (rt_max - rt_min) * 0.1 if rt_max > rt_min else 0.1
rt_floor = rt_min - margin
rt_ceil = rt_max + margin
variables["reward_trace"] = [(v - rt_floor) / (rt_ceil - rt_floor) for v in rt]

# Extract modes from control surface traces
modes = [s["mode"] for s in surface_data]

# Extract reward events
reward_totals = [r["total"] for r in reward_data]

# ── Identify key moments ──────────────────────────────────────────────────────

# Find ticks where reward was positive (agent wrote a successful fix)
positive_reward_ticks = [i for i, r in enumerate(reward_totals) if r > 0]
# Find edit ticks
edit_ticks = [i for i, m in enumerate(modes) if "edit" in m]

# ── Create figure ─────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(16, 9), dpi=300, facecolor=DARK_BG)

# Main axes for the state traces, with room for mode strip at top
ax_main = fig.add_axes([0.08, 0.10, 0.78, 0.72], facecolor=DARK_BG)
ax_mode = fig.add_axes([0.08, 0.84, 0.78, 0.06], facecolor=DARK_BG, sharex=ax_main)

# ── Mode strip ───────────────────────────────────────────────────────────────

for i, mode in enumerate(modes):
    color = MODE_COLORS.get(mode, "#444444")
    ax_mode.barh(0, 1, left=i, height=1, color=color, edgecolor="none", alpha=0.85)
    # Label every other tick to avoid crowding
    if i % 2 == 0:
        short = MODE_LABELS.get(mode, mode)
        ax_mode.text(i + 0.5, 0, short, ha="center", va="center",
                     fontsize=5.5, fontweight="bold", color="white",
                     path_effects=[pe.withStroke(linewidth=1.5, foreground=DARK_BG)])

ax_mode.set_xlim(-0.5, n_ticks - 0.5)
ax_mode.set_ylim(-0.5, 0.5)
ax_mode.set_yticks([])
ax_mode.tick_params(labelbottom=False, bottom=False, left=False)
for spine in ax_mode.spines.values():
    spine.set_visible(False)
ax_mode.set_ylabel("mode", fontsize=8, color=SUBTLE_TEXT, rotation=0,
                    labelpad=30, va="center")

# Mode legend (compact, top right)
mode_seen = []
for m in modes:
    if m not in mode_seen:
        mode_seen.append(m)
mode_patches = [mpatches.Patch(color=MODE_COLORS[m], label=MODE_LABELS.get(m, m))
                for m in mode_seen]

# ── Plot state variable traces ────────────────────────────────────────────────

# Add subtle vertical bands for edit ticks
for t in edit_ticks:
    ax_main.axvspan(t - 0.3, t + 0.3, alpha=0.08, color="#E07C3E", zorder=0)

for var_name, color in STATE_COLORS.items():
    values = variables[var_name]
    label = STATE_LABELS[var_name]
    ax_main.plot(ticks, values, color=color, linewidth=2.5, label=label,
                 alpha=0.92, zorder=5)
    # Add a subtle glow effect
    ax_main.plot(ticks, values, color=color, linewidth=5, alpha=0.12, zorder=4)

# ── Annotations ───────────────────────────────────────────────────────────────

annotation_style = dict(
    fontsize=9,
    color=TEXT_COLOR,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.3", facecolor="#161b22", edgecolor="#30363d",
              linewidth=0.8, alpha=0.95),
    arrowprops=dict(arrowstyle="->", color="#58a6ff", lw=1.5,
                    connectionstyle="arc3,rad=0.2"),
    zorder=10,
)

# Annotation 1: tick 1 — first edit with persistence spike
# Persistence spikes at tick 1 (0.534)
ax_main.annotate(
    "first edit attempt",
    xy=(1, variables["persistence"][1]),
    xytext=(3.5, 0.85),
    **annotation_style,
)

# Annotation 2: tick 9 — positive reward, novelty_seek spikes
# This is where the agent gets a reward and novelty_seek jumps
ax_main.annotate(
    "reward signal\n(tests improve)",
    xy=(9, variables["novelty_seek"][9]),
    xytext=(12, 0.78),
    **annotation_style,
)

# Annotation 3: stability stays high throughout — the agent is cautious
ax_main.annotate(
    "stability dominates\n(conservative agent)",
    xy=(7, variables["stability"][7]),
    xytext=(1.5, 0.08),
    fontsize=9,
    color=TEXT_COLOR,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.3", facecolor="#161b22", edgecolor="#30363d",
              linewidth=0.8, alpha=0.95),
    arrowprops=dict(arrowstyle="->", color="#58a6ff", lw=1.5,
                    connectionstyle="arc3,rad=-0.2"),
    zorder=10,
)

# ── Styling ───────────────────────────────────────────────────────────────────

ax_main.set_xlim(-0.5, n_ticks - 0.5)
ax_main.set_ylim(-0.05, 1.05)
ax_main.set_xlabel("Tick", fontsize=12, color=TEXT_COLOR, labelpad=10)
ax_main.set_ylabel("State value", fontsize=12, color=TEXT_COLOR, labelpad=10)
ax_main.set_xticks(range(n_ticks))
ax_main.set_xticklabels(range(n_ticks), fontsize=8, color=SUBTLE_TEXT)
ax_main.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax_main.set_yticklabels(["0", "0.25", "0.5", "0.75", "1.0"],
                         fontsize=8, color=SUBTLE_TEXT)

# Grid
ax_main.grid(True, axis="both", color=GRID_COLOR, linewidth=0.5, alpha=0.5)
ax_main.set_axisbelow(True)

# Spines
for spine in ax_main.spines.values():
    spine.set_color(GRID_COLOR)
ax_main.tick_params(colors=SUBTLE_TEXT, length=3)

# Legend — right side, outside the plot
legend = ax_main.legend(
    loc="upper left",
    bbox_to_anchor=(1.01, 1.0),
    fontsize=9,
    frameon=True,
    facecolor="#161b22",
    edgecolor="#30363d",
    labelcolor=TEXT_COLOR,
    title="State variables",
    title_fontsize=10,
    borderpad=0.8,
    handlelength=2,
)
legend.get_title().set_color(TEXT_COLOR)

# Mode legend below the state legend
mode_legend = ax_main.legend(
    handles=mode_patches,
    loc="lower left",
    bbox_to_anchor=(1.01, 0.0),
    fontsize=8,
    frameon=True,
    facecolor="#161b22",
    edgecolor="#30363d",
    labelcolor=TEXT_COLOR,
    title="Modes",
    title_fontsize=9,
    borderpad=0.8,
    handlelength=1.5,
)
mode_legend.get_title().set_color(TEXT_COLOR)
# Re-add state legend since matplotlib replaces it
ax_main.add_artist(legend)

# ── Title ─────────────────────────────────────────────────────────────────────

fig.text(0.08, 0.95, "Agent state evolution",
         fontsize=20, fontweight="bold", color=TEXT_COLOR, ha="left")
fig.text(0.08, 0.915, "Live NEURON controller, Level 2",
         fontsize=13, color=SUBTLE_TEXT, ha="left")

# ── Edit tick indicator label ─────────────────────────────────────────────────

# Small note about the orange bands
fig.text(0.08, 0.05, "Orange bands = edit ticks",
         fontsize=7.5, color="#E07C3E", alpha=0.6, ha="left")

# ── Save ──────────────────────────────────────────────────────────────────────

out_path = OUT_DIR / "v5_state_traces.png"
fig.savefig(out_path, dpi=300, facecolor=DARK_BG, edgecolor="none",
            bbox_inches="tight", pad_inches=0.3)
plt.close(fig)
print(f"Saved: {out_path}")
