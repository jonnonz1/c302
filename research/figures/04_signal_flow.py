#!/usr/bin/env python3
"""Signal Flow Diagram.

Shows the complete feedback loop of the c302 connectome controller:
experiment signals -> stimulus injection -> neural dynamics ->
state variables -> mode selection -> agent action -> experiment signals.

Uses matplotlib patches and annotations for a clean architectural diagram.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(18, 12))
fig.patch.set_facecolor("#0F172A")
ax.set_facecolor("#0F172A")
ax.set_xlim(0, 18)
ax.set_ylim(0, 12)
ax.axis("off")

# ---------- Style constants ----------

BOX_ALPHA = 0.9
ARROW_COLOR = "#94A3B8"
ARROW_STYLE = "->,head_length=8,head_width=5"


def draw_box(ax, x, y, w, h, label, sublabel=None, color="#1E40AF",
             text_color="white", fontsize=11, sublabel_fontsize=8,
             corner_radius=0.3):
    """Draw a rounded box with label."""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.15,rounding_size={corner_radius}",
        facecolor=color, edgecolor="#475569", linewidth=1.5,
        alpha=BOX_ALPHA, zorder=3,
    )
    ax.add_patch(box)
    cx, cy = x + w / 2, y + h / 2
    if sublabel:
        ax.text(cx, cy + 0.15, label, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", color=text_color, zorder=4)
        ax.text(cx, cy - 0.25, sublabel, ha="center", va="center",
                fontsize=sublabel_fontsize, color="#CBD5E1", zorder=4,
                fontfamily="monospace", alpha=0.8)
    else:
        ax.text(cx, cy, label, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", color=text_color, zorder=4)
    return (cx, cy)


def draw_arrow(ax, start, end, label=None, color=ARROW_COLOR, curved=0,
               label_offset=(0, 0.25), fontsize=8):
    """Draw a curved arrow with optional label."""
    arrow = FancyArrowPatch(
        start, end,
        arrowstyle=ARROW_STYLE,
        connectionstyle=f"arc3,rad={curved}",
        color=color, linewidth=2.0, zorder=2,
        mutation_scale=15,
    )
    ax.add_patch(arrow)
    if label:
        mx = (start[0] + end[0]) / 2 + label_offset[0]
        my = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(mx, my, label, ha="center", va="center",
                fontsize=fontsize, color="#CBD5E1", style="italic",
                zorder=5, bbox=dict(boxstyle="round,pad=0.15",
                                     facecolor="#0F172A", edgecolor="none", alpha=0.8))


# ---------- Main boxes (clockwise from top-left) ----------

# 1. Experiment Environment (top-left)
draw_box(ax, 0.5, 9.5, 4.5, 1.8, "Experiment Environment",
         "test_pass_rate, error_count\nfiles_changed, iterations",
         color="#1E3A5F")

# 2. Stimulus Injection (left)
draw_box(ax, 0.5, 6.5, 4.5, 1.8, "Stimulus Injection",
         "PVC <- (1-test_pass)\nASER <- neg_reward\nASEL <- pos_reward\nAVA <- errors",
         color="#164E63", sublabel_fontsize=7)

# 3. NEURON Simulation (center, large)
box_neuron_x, box_neuron_y = 6.5, 5.0
box_neuron_w, box_neuron_h = 5.5, 4.8

neuron_box = FancyBboxPatch(
    (box_neuron_x, box_neuron_y), box_neuron_w, box_neuron_h,
    boxstyle="round,pad=0.2,rounding_size=0.4",
    facecolor="#1E1B4B", edgecolor="#6366F1", linewidth=2.5,
    alpha=0.9, zorder=3,
)
ax.add_patch(neuron_box)

cx = box_neuron_x + box_neuron_w / 2
ax.text(cx, box_neuron_y + box_neuron_h - 0.45, "c302 NEURON Simulation",
        ha="center", fontsize=14, fontweight="bold", color="#A5B4FC", zorder=4)
ax.text(cx, box_neuron_y + box_neuron_h - 0.9, "14 neurons | 63 chem. synapses | 14 gap junctions",
        ha="center", fontsize=8, color="#818CF8", zorder=4)

# Sub-boxes inside NEURON
inner_y = box_neuron_y + 0.4
draw_box(ax, 7.0, inner_y + 2.2, 2.0, 0.9, "Sensory",
         "ASE, AWC", color="#1E40AF", fontsize=9, sublabel_fontsize=7)
draw_box(ax, 9.5, inner_y + 2.2, 2.0, 0.9, "Command",
         "AVA-AVE", color="#991B1B", fontsize=9, sublabel_fontsize=7)
draw_box(ax, 7.0, inner_y + 0.6, 2.0, 0.9, "PVC",
         "Forward", color="#166534", fontsize=9, sublabel_fontsize=7)
draw_box(ax, 9.5, inner_y + 0.6, 2.0, 0.9, "Synaptic\nDynamics",
         "dt=0.05ms", color="#44403C", fontsize=9, sublabel_fontsize=7)

# Inner arrows
draw_arrow(ax, (9.0, inner_y + 2.65), (9.5, inner_y + 2.65), color="#6366F1")
draw_arrow(ax, (9.5, inner_y + 1.05), (9.0, inner_y + 1.05), color="#6366F1")
draw_arrow(ax, (10.5, inner_y + 2.2), (10.5, inner_y + 1.5), color="#6366F1")

# 4. State Variables (right)
draw_box(ax, 13.0, 6.5, 4.0, 1.8, "State Variables",
         "arousal, novelty_seek\nstability, persistence\nerror_aversion, reward_trace",
         color="#4C1D95", sublabel_fontsize=7)

# 5. Mode Selection (top-right)
draw_box(ax, 13.0, 9.5, 4.0, 1.8, "Mode Selection",
         "diagnose | search | edit-small\nedit-large | run-tests\nreflect | stop",
         color="#7C2D12", sublabel_fontsize=7)

# 6. Control Surface (top-center)
draw_box(ax, 6.5, 10.2, 5.5, 1.0, "Control Surface",
         "mode, temperature, token_budget, aggression",
         color="#1F2937", fontsize=10, sublabel_fontsize=7)

# 7. LLM Agent (center-top)
draw_box(ax, 7.5, 2.0, 3.5, 1.5, "LLM Agent",
         "Claude + tool use", color="#312E81")

# 8. Reward (bottom)
draw_box(ax, 6.0, 0.3, 6.5, 1.0, "Reward Signal",
         "+1 test fix, -0.5 regression, +0.5 error fix",
         color="#713F12", fontsize=10, sublabel_fontsize=7)

# ---------- Arrows (the feedback loop) ----------

# Experiment -> Stimulus (down)
draw_arrow(ax, (2.75, 9.5), (2.75, 8.3), "signals", label_offset=(0.8, 0))

# Stimulus -> NEURON (right)
draw_arrow(ax, (5.0, 7.4), (6.5, 7.4), "IClamp (nA)")

# NEURON -> State Variables (right)
draw_arrow(ax, (12.0, 7.4), (13.0, 7.4), "activity\n(tau=50ms)",
           label_offset=(0, 0.35))

# State -> Mode Selection (up)
draw_arrow(ax, (15.0, 8.3), (15.0, 9.5), "priority\nrules",
           label_offset=(0.8, 0))

# Mode Selection -> Control Surface (left)
draw_arrow(ax, (13.0, 10.7), (12.0, 10.7), "mode +\nparams",
           label_offset=(0, 0.35))

# Control Surface -> Agent (down, left side)
draw_arrow(ax, (7.5, 10.2), (7.5, 3.5), "system prompt\n+ tool mask",
           label_offset=(-1.3, 0), curved=-0.2)

# Agent -> Experiment (up to top-left, big curve)
draw_arrow(ax, (7.5, 2.75), (2.75, 2.75), color="#22C55E", curved=-0.1)
draw_arrow(ax, (2.75, 2.75), (2.75, 9.5), "code changes",
           label_offset=(-1.0, 0), color="#22C55E", curved=0)

# Experiment -> Reward (down)
draw_arrow(ax, (4.0, 9.5), (7.0, 1.3), "test results", curved=-0.3,
           color="#FBBF24", label_offset=(-0.5, 0.5))

# Reward -> Stimulus (loop)
draw_arrow(ax, (6.0, 0.8), (1.5, 0.8), color="#FBBF24", curved=0)
draw_arrow(ax, (1.5, 0.8), (1.5, 7.4), "reward", color="#FBBF24",
           label_offset=(-0.7, 0), curved=0)
draw_arrow(ax, (1.5, 7.4), (0.5, 7.4), color="#FBBF24", curved=0)

# ---------- Title ----------

ax.text(9, 11.8, "c302 Connectome Controller: Signal Flow",
        ha="center", va="center", fontsize=20, fontweight="bold", color="white")

# Time annotation
ax.text(9, 0.05, "One tick = 83ms simulated time  |  ~1660 NEURON integration steps  |  dt=0.05ms",
        ha="center", fontsize=9, color="#64748B", fontfamily="monospace")

# ---------- Save ----------

out = "/Users/jonno/workspace/c302/research/figures/04_signal_flow.png"
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"Saved: {out}")
