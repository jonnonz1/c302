#!/usr/bin/env python3
"""V4 Neural Activity Heatmap — "Watch the worm think."

Renders a 14-neuron x 18-tick heatmap from a live L2 NEURON simulation,
showing real-time neural responses to agent actions.

Data source: live-battery-20260403-224824-01 (18 ticks, L2 run).
"""

import json
import numpy as np
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
import _font_setup  # noqa: F401 — registers Inter + JetBrains Mono
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import FancyBboxPatch
import matplotlib.gridspec as gridspec

# ── Paths ──────────────────────────────────────────────────────────────
BASE = "/Users/jonno/workspace/c302/research/experiments/live-battery-20260403-224824-01"
OUT  = "/Users/jonno/workspace/c302/research/figures/v4_neural_heatmap.png"

# ── Load data ──────────────────────────────────────────────────────────
with open(f"{BASE}/neuron-activity-traces.json") as f:
    neuron_traces = json.load(f)
with open(f"{BASE}/reward-history.json") as f:
    rewards = json.load(f)
with open(f"{BASE}/control-surface-traces.json") as f:
    control_traces = json.load(f)

n_ticks = len(neuron_traces)

# ── Neuron ordering (sensory top, command bottom) ──────────────────────
sensory_neurons = ["ASEL", "ASER", "AWCL", "AWCR"]
command_neurons = ["AVAL", "AVAR", "AVBL", "AVBR", "AVDL", "AVDR",
                   "AVEL", "AVER", "PVCL", "PVCR"]
all_neurons = sensory_neurons + command_neurons
n_neurons = len(all_neurons)

# ── Build activity matrix (neurons x ticks) ────────────────────────────
activity = np.zeros((n_neurons, n_ticks))
for t, tick in enumerate(neuron_traces):
    for i, neuron in enumerate(sensory_neurons):
        activity[i, t] = tick["sensory"].get(neuron, 0.0)
    for j, neuron in enumerate(command_neurons):
        activity[len(sensory_neurons) + j, t] = tick["command"].get(neuron, 0.0)

# ── Extract modes and rewards ──────────────────────────────────────────
modes = [ct["mode"] for ct in control_traces]
reward_totals = [r["total"] for r in rewards]

# ── Mode colors (consistent with V1/V2) ───────────────────────────────
mode_colors = {
    "diagnose":   "#60A5FA",
    "search":     "#A78BFA",
    "edit-small": "#34D399",
    "edit-large": "#FBBF24",
    "run-tests":  "#F87171",
    "reflect":    "#FB923C",
    "stop":       "#94A3B8",
}
mode_abbrev = {
    "diagnose": "DX", "search": "SR", "edit-small": "ES",
    "edit-large": "EL", "run-tests": "RT", "reflect": "RF", "stop": "ST",
}

# ── Style constants ────────────────────────────────────────────────────
BG_COLOR   = "#0d1117"
TEXT_COLOR  = "#c9d1d9"
GRID_COLOR = "#21262d"
DIVIDER_COLOR = "#58a6ff"

# ── Identify annotation moments ───────────────────────────────────────
# 1. First edit mode entry (tick 2 — agent starts editing)
first_edit_tick = next(i for i, m in enumerate(modes) if "edit" in m)
# 2. PVCL spike — PVC neurons light up from test failure signal (tick 2 has PVCL=0.4683)
pvcl_vals = activity[all_neurons.index("PVCL"), :]
pvcl_spike_tick = int(np.argmax(pvcl_vals))  # tick 8: PVCL=0.5017
# 3. ASEL activation — sensory neurons respond to positive reward (tick 3)
asel_vals = activity[all_neurons.index("ASEL"), :]
# Find tick where ASEL first goes high AND reward is positive nearby
asel_high_ticks = np.where(asel_vals > 0.4)[0]
# Tick 10 has ASEL=0.428 and follows reward at tick 9
asel_reward_tick = 10 if 10 in asel_high_ticks else int(asel_high_ticks[0]) if len(asel_high_ticks) > 0 else 3

# ── Create figure ──────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 8), facecolor=BG_COLOR)

# GridSpec: mode strip (top, thin), heatmap (main), reward sparkline (bottom, thin)
gs = gridspec.GridSpec(
    3, 2,
    height_ratios=[0.06, 1, 0.08],
    width_ratios=[1, 0.025],
    hspace=0.08, wspace=0.03,
    left=0.08, right=0.92, top=0.88, bottom=0.08,
)

ax_mode = fig.add_subplot(gs[0, 0])   # mode strip
ax_heat = fig.add_subplot(gs[1, 0])   # main heatmap
ax_cbar = fig.add_subplot(gs[1, 1])   # colorbar
ax_reward = fig.add_subplot(gs[2, 0]) # reward sparkline

# ── Mode strip ─────────────────────────────────────────────────────────
ax_mode.set_facecolor(BG_COLOR)
for t in range(n_ticks):
    c = mode_colors.get(modes[t], "#94A3B8")
    ax_mode.add_patch(plt.Rectangle((t, 0), 1, 1, facecolor=c, edgecolor=BG_COLOR,
                                     linewidth=0.5))
    ax_mode.text(t + 0.5, 0.5, mode_abbrev.get(modes[t], "?"),
                 ha="center", va="center", fontsize=6.5, fontweight="bold",
                 color="#0d1117", fontfamily="JetBrains Mono")

ax_mode.set_xlim(0, n_ticks)
ax_mode.set_ylim(0, 1)
ax_mode.set_xticks([])
ax_mode.set_yticks([])
ax_mode.set_ylabel("Mode", fontsize=9, color=TEXT_COLOR, fontweight="bold",
                    rotation=0, labelpad=35, va="center")
for spine in ax_mode.spines.values():
    spine.set_visible(False)

# ── Heatmap ────────────────────────────────────────────────────────────
ax_heat.set_facecolor(BG_COLOR)

# Use 'inferno' — dark-to-bright, perceptually uniform
cmap = plt.cm.inferno

im = ax_heat.imshow(
    activity,
    aspect="auto",
    cmap=cmap,
    vmin=0, vmax=1,
    interpolation="nearest",
    extent=[0, n_ticks, n_neurons, 0],
)

# Horizontal divider between sensory and command groups
divider_y = len(sensory_neurons)
ax_heat.axhline(y=divider_y, color=DIVIDER_COLOR, linewidth=1.5, alpha=0.7)

# Subtle grid lines between neurons
for i in range(n_neurons + 1):
    ax_heat.axhline(y=i, color=GRID_COLOR, linewidth=0.3, alpha=0.5)
for t in range(n_ticks + 1):
    ax_heat.axvline(x=t, color=GRID_COLOR, linewidth=0.3, alpha=0.5)

# Y-axis: neuron names
ax_heat.set_yticks([i + 0.5 for i in range(n_neurons)])
ax_heat.set_yticklabels(all_neurons, fontsize=10, fontfamily="JetBrains Mono",
                         fontweight="bold", color=TEXT_COLOR)

# Color sensory neuron labels differently
for i, label in enumerate(ax_heat.get_yticklabels()):
    if i < len(sensory_neurons):
        label.set_color("#FCA5A5")  # warm red for sensory
    else:
        label.set_color("#93C5FD")  # cool blue for command

# X-axis: tick numbers
ax_heat.set_xticks([t + 0.5 for t in range(n_ticks)])
ax_heat.set_xticklabels([str(t + 1) for t in range(n_ticks)], fontsize=9,
                          color=TEXT_COLOR, fontfamily="JetBrains Mono")
ax_heat.set_xlabel("")

# Group labels on the far left
fig.text(0.015, 0.68, "SENSORY", fontsize=9, color="#FCA5A5", fontweight="bold",
         rotation=90, va="center", ha="center", fontfamily="JetBrains Mono")
fig.text(0.015, 0.43, "COMMAND", fontsize=9, color="#93C5FD", fontweight="bold",
         rotation=90, va="center", ha="center", fontfamily="JetBrains Mono")

# Remove spines
for spine in ax_heat.spines.values():
    spine.set_color(GRID_COLOR)
    spine.set_linewidth(0.5)

ax_heat.tick_params(axis="both", which="both", length=0, pad=6)

# ── Annotations ────────────────────────────────────────────────────────
annotation_style = dict(
    fontsize=8, fontweight="bold", color="#F0F6FC",
    fontfamily="JetBrains Mono",
    bbox=dict(boxstyle="round,pad=0.3", facecolor="#161b22", edgecolor="#30363d",
              linewidth=0.8, alpha=0.95),
)
arrow_style = dict(
    arrowstyle="->,head_width=0.15,head_length=0.1",
    color="#58a6ff",
    linewidth=1.2,
    connectionstyle="arc3,rad=0.15",
)

# Annotation 1: Agent enters edit mode (tick 2) — point at the mode strip area
# Place label to the right of the arrow target, inside the heatmap region
ax_heat.annotate(
    "agent enters\nedit mode",
    xy=(first_edit_tick + 0.5, 1.5),
    xytext=(first_edit_tick + 4.0, 1.5),
    **annotation_style,
    arrowprops=dict(**arrow_style),
    ha="center", va="center",
)

# Annotation 2: PVCL spike at tick 8 — test failure signal
pvcl_row = all_neurons.index("PVCL")
ax_heat.annotate(
    "PVCL spike (test failures)",
    xy=(pvcl_spike_tick + 0.5, pvcl_row + 0.5),
    xytext=(pvcl_spike_tick + 5.0, pvcl_row - 1.5),
    **annotation_style,
    arrowprops=dict(arrowstyle=arrow_style["arrowstyle"], color=arrow_style["color"],
                    linewidth=arrow_style["linewidth"], connectionstyle="arc3,rad=0.2"),
    ha="center", va="center",
)

# Annotation 3: ASEL lights up — positive reward response (tick 10)
asel_row = all_neurons.index("ASEL")
ax_heat.annotate(
    "ASEL fires (+reward)",
    xy=(asel_reward_tick + 0.5, asel_row + 0.5),
    xytext=(asel_reward_tick + 4.5, asel_row + 3.0),
    **annotation_style,
    arrowprops=dict(**arrow_style),
    ha="center", va="center",
)

# ── Colorbar ───────────────────────────────────────────────────────────
cb = fig.colorbar(im, cax=ax_cbar)
cb.set_label("Activity (0\u20131)", fontsize=10, color=TEXT_COLOR, fontweight="bold",
             labelpad=10)
cb.ax.tick_params(colors=TEXT_COLOR, labelsize=8)
cb.outline.set_edgecolor(GRID_COLOR)
cb.outline.set_linewidth(0.5)

# ── Reward sparkline ───────────────────────────────────────────────────
ax_reward.set_facecolor(BG_COLOR)
for t in range(n_ticks):
    r = reward_totals[t]
    color = "#34D399" if r > 0 else ("#F87171" if r < 0 else "#30363d")
    ax_reward.bar(t + 0.5, r, width=0.8, color=color, edgecolor="none", alpha=0.9)

ax_reward.axhline(y=0, color="#484f58", linewidth=0.5)
ax_reward.set_xlim(0, n_ticks)
ax_reward.set_xticks([])
ax_reward.set_ylabel("Reward", fontsize=8, color=TEXT_COLOR, fontweight="bold",
                      rotation=0, labelpad=35, va="center")
ax_reward.tick_params(axis="y", colors=TEXT_COLOR, labelsize=7)
for spine in ax_reward.spines.values():
    spine.set_visible(False)

# ── Title ──────────────────────────────────────────────────────────────
fig.suptitle(
    "Live NEURON simulation \u2014 14 neurons responding to agent actions",
    fontsize=16, fontweight="bold", color="#F0F6FC",
    fontfamily="JetBrains Mono",
    y=0.97,
)

# Subtitle with run info
fig.text(
    0.5, 0.935,
    f"L2 run  \u00b7  {n_ticks} ticks  \u00b7  final test pass rate: 96.7%",
    ha="center", fontsize=10, color="#8b949e", fontfamily="JetBrains Mono",
)

# ── Mode legend (bottom) ──────────────────────────────────────────────
legend_items = []
for mode, abbr in mode_abbrev.items():
    c = mode_colors[mode]
    legend_items.append(f"{abbr}={mode}")
legend_text = "    ".join(legend_items)
fig.text(0.5, 0.015, legend_text, ha="center", fontsize=7.5, color="#8b949e",
         fontfamily="JetBrains Mono")

# ── Save ───────────────────────────────────────────────────────────────
fig.savefig(OUT, dpi=300, facecolor=BG_COLOR, bbox_inches="tight", pad_inches=0.3)
plt.close(fig)
print(f"Saved: {OUT}")
print(f"  Resolution: 16x8 @ 300 DPI")
print(f"  Neurons: {n_neurons} ({len(sensory_neurons)} sensory + {len(command_neurons)} command)")
print(f"  Ticks: {n_ticks}")
