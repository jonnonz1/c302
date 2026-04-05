#!/usr/bin/env python3
"""c302 Network Topology Diagram.

Visualizes the 14-neuron c302 subcircuit with:
- Chemical synapses as directed arrows (thickness = weight)
- Gap junctions as undirected dashed lines (thickness = weight)
- Neurons color-coded by functional class
"""

import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

# Try networkx, fall back to manual layout
try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False

# ---------- Data from live.py ----------

NEURON_NAMES = [
    "ASEL", "ASER", "AWCL", "AWCR",
    "AVAL", "AVAR", "AVBL", "AVBR",
    "AVDL", "AVDR", "AVEL", "AVER",
    "PVCL", "PVCR",
]

CHEMICAL_SYNAPSES = [
    ("ASEL", "AWCL", 4.0), ("ASEL", "AWCR", 1.0),
    ("ASER", "AWCL", 1.0), ("ASER", "AWCR", 1.0),
    ("AVAL", "AVAR", 2.0), ("AVAL", "AVBR", 1.0),
    ("AVAL", "AVDL", 1.0), ("AVAL", "PVCL", 10.0), ("AVAL", "PVCR", 6.0),
    ("AVAR", "AVAL", 1.0), ("AVAR", "AVBL", 1.0),
    ("AVAR", "AVDL", 1.0), ("AVAR", "AVDR", 2.0),
    ("AVAR", "AVEL", 2.0), ("AVAR", "AVER", 2.0),
    ("AVAR", "PVCL", 7.0), ("AVAR", "PVCR", 5.0),
    ("AVBL", "AVAL", 7.0), ("AVBL", "AVAR", 7.0), ("AVBL", "AVBR", 1.0),
    ("AVBL", "AVDL", 1.0), ("AVBL", "AVDR", 2.0),
    ("AVBL", "AVEL", 1.0), ("AVBL", "AVER", 2.0),
    ("AVBR", "AVAL", 6.0), ("AVBR", "AVAR", 7.0), ("AVBR", "AVBL", 1.0),
    ("AVDL", "AVAL", 13.0), ("AVDL", "AVAR", 19.0), ("AVDL", "PVCL", 1.0),
    ("AVDR", "AVAL", 16.0), ("AVDR", "AVAR", 15.0),
    ("AVDR", "AVBL", 1.0), ("AVDR", "AVDL", 2.0),
    ("AVEL", "AVAL", 12.0), ("AVEL", "AVAR", 7.0), ("AVEL", "PVCR", 1.0),
    ("AVER", "AVAL", 7.0), ("AVER", "AVAR", 16.0), ("AVER", "AVDR", 1.0),
    ("AWCL", "ASEL", 1.0), ("AWCL", "AVAL", 1.0), ("AWCL", "AWCR", 1.0),
    ("AWCR", "ASEL", 1.0), ("AWCR", "AWCL", 5.0),
    ("PVCL", "AVAL", 1.0), ("PVCL", "AVAR", 4.0),
    ("PVCL", "AVBL", 5.0), ("PVCL", "AVBR", 12.0),
    ("PVCL", "AVDL", 5.0), ("PVCL", "AVDR", 2.0),
    ("PVCL", "AVEL", 2.0), ("PVCL", "AVER", 1.0), ("PVCL", "PVCR", 2.0),
    ("PVCR", "AVAL", 7.0), ("PVCR", "AVAR", 7.0),
    ("PVCR", "AVBL", 8.0), ("PVCR", "AVBR", 6.0),
    ("PVCR", "AVDL", 5.0), ("PVCR", "AVDR", 1.0),
    ("PVCR", "AVEL", 1.0), ("PVCR", "AVER", 1.0), ("PVCR", "PVCL", 3.0),
]

ELECTRICAL_SYNAPSES = [
    ("AVAL", "AVAR", 5.0), ("AVAL", "PVCL", 2.0), ("AVAL", "PVCR", 5.0),
    ("AVAR", "AVAL", 5.0), ("AVAR", "PVCR", 3.0),
    ("AVBL", "AVBR", 3.0), ("AVBR", "AVBL", 3.0),
    ("AVEL", "AVER", 1.0), ("AVER", "AVEL", 1.0),
    ("PVCL", "AVAL", 2.0), ("PVCL", "PVCR", 5.0),
    ("PVCR", "AVAL", 5.0), ("PVCR", "AVAR", 3.0), ("PVCR", "PVCL", 5.0),
]

# Functional classification
SENSORY = {"ASEL", "ASER", "AWCL", "AWCR"}
COMMAND = {"AVAL", "AVAR", "AVBL", "AVBR", "AVDL", "AVDR", "AVEL", "AVER"}
FORWARD = {"PVCL", "PVCR"}

# Colors
COLOR_SENSORY = "#3B82F6"   # Blue
COLOR_COMMAND = "#EF4444"   # Red
COLOR_FORWARD = "#22C55E"   # Green

def get_color(name):
    if name in SENSORY:
        return COLOR_SENSORY
    elif name in COMMAND:
        return COLOR_COMMAND
    else:
        return COLOR_FORWARD

# ---------- Layout ----------

# Manual circular-tier layout: sensory top, command middle ring, PVC bottom
def manual_layout():
    pos = {}
    # Sensory neurons: top arc
    sensory_list = ["ASEL", "AWCL", "AWCR", "ASER"]
    for i, name in enumerate(sensory_list):
        angle = math.pi * 0.55 + (i / (len(sensory_list) - 1)) * math.pi * 0.35
        pos[name] = (2.8 * math.cos(angle), 2.8 * math.sin(angle) + 0.5)

    # Command interneurons: middle ring
    command_list = ["AVBL", "AVDL", "AVEL", "AVAL", "AVAR", "AVER", "AVDR", "AVBR"]
    for i, name in enumerate(command_list):
        angle = math.pi * 0.8 + (i / len(command_list)) * math.pi * 1.6
        pos[name] = (1.8 * math.cos(angle), 1.8 * math.sin(angle) - 0.3)

    # Forward locomotion: bottom
    pos["PVCL"] = (-0.6, -2.6)
    pos["PVCR"] = (0.6, -2.6)

    return pos


# ---------- Draw ----------

fig, ax = plt.subplots(1, 1, figsize=(14, 14))
ax.set_aspect("equal")
ax.set_xlim(-4.2, 4.2)
ax.set_ylim(-4.2, 4.2)
ax.axis("off")
fig.patch.set_facecolor("#0F172A")
ax.set_facecolor("#0F172A")

pos = manual_layout()

# Deduplicate gap junctions (keep unique pairs)
gap_pairs = set()
for a, b, w in ELECTRICAL_SYNAPSES:
    key = tuple(sorted([a, b]))
    gap_pairs.add((key[0], key[1], w))

# Draw gap junctions first (behind everything)
max_gap_w = max(w for _, _, w in gap_pairs)
for a, b, w in gap_pairs:
    x0, y0 = pos[a]
    x1, y1 = pos[b]
    lw = 0.5 + 2.5 * (w / max_gap_w)
    ax.plot([x0, x1], [y0, y1], color="#FBBF24", alpha=0.35, linewidth=lw,
            linestyle=(0, (4, 3)), zorder=1)

# Draw chemical synapses as curved arrows
max_chem_w = max(w for _, _, w in CHEMICAL_SYNAPSES)

for pre, post, w in CHEMICAL_SYNAPSES:
    x0, y0 = pos[pre]
    x1, y1 = pos[post]

    # Shorten arrow to not overlap with node circles
    dx, dy = x1 - x0, y1 - y0
    dist = math.sqrt(dx * dx + dy * dy)
    if dist < 0.01:
        continue
    shrink = 0.38 / dist
    sx0 = x0 + dx * shrink
    sy0 = y0 + dy * shrink
    sx1 = x1 - dx * shrink
    sy1 = y1 - dy * shrink

    alpha = 0.15 + 0.45 * (w / max_chem_w)
    lw = 0.3 + 2.0 * (w / max_chem_w)

    # Curvature to separate bidirectional edges
    # Check if reverse edge exists
    has_reverse = any(p == post and q == pre for p, q, _ in CHEMICAL_SYNAPSES)
    rad = 0.15 if has_reverse else 0.05

    arrow = FancyArrowPatch(
        (sx0, sy0), (sx1, sy1),
        arrowstyle="->,head_length=6,head_width=3",
        connectionstyle=f"arc3,rad={rad}",
        color="#94A3B8",
        alpha=alpha,
        linewidth=lw,
        zorder=2,
    )
    ax.add_patch(arrow)

# Draw neuron nodes
node_size = 0.36
for name in NEURON_NAMES:
    x, y = pos[name]
    color = get_color(name)

    # Glow effect
    for r, a in [(node_size * 1.8, 0.06), (node_size * 1.4, 0.12)]:
        circle = plt.Circle((x, y), r, color=color, alpha=a, zorder=3)
        ax.add_patch(circle)

    # Main node
    circle = plt.Circle((x, y), node_size, color=color, alpha=0.9, zorder=4,
                         edgecolor="white", linewidth=1.2)
    ax.add_patch(circle)

    # Label
    ax.text(x, y, name, ha="center", va="center", fontsize=7,
            fontweight="bold", color="white", zorder=5,
            fontfamily="monospace")

# Legend
legend_items = [
    mpatches.Patch(facecolor=COLOR_SENSORY, edgecolor="white", label="Sensory (ASE, AWC)"),
    mpatches.Patch(facecolor=COLOR_COMMAND, edgecolor="white", label="Command interneurons (AVA-AVE)"),
    mpatches.Patch(facecolor=COLOR_FORWARD, edgecolor="white", label="Forward locomotion (PVC)"),
]
leg = ax.legend(handles=legend_items, loc="lower left", fontsize=10,
                frameon=True, facecolor="#1E293B", edgecolor="#475569",
                labelcolor="white", borderpad=1.0)

# Connection type annotations
ax.annotate("", xy=(3.0, -3.4), xytext=(2.0, -3.4),
            arrowprops=dict(arrowstyle="->", color="#94A3B8", lw=1.5))
ax.text(3.15, -3.4, "Chemical synapse", color="#94A3B8", fontsize=9, va="center")

ax.plot([2.0, 3.0], [-3.7, -3.7], color="#FBBF24", alpha=0.6, linewidth=1.5,
        linestyle=(0, (4, 3)))
ax.text(3.15, -3.7, "Gap junction", color="#FBBF24", fontsize=9, va="center", alpha=0.8)

ax.text(2.5, -3.05, "Line thickness = synaptic weight", color="#64748B",
        fontsize=8, va="center", ha="center")

# Title
ax.text(0, 3.7, "c302 Connectome Controller", ha="center", va="center",
        fontsize=20, fontweight="bold", color="white", fontfamily="sans-serif")
ax.text(0, 3.3, "14 neurons  |  63 chemical synapses  |  14 gap junctions",
        ha="center", va="center", fontsize=12, color="#94A3B8")

# Save
out = "/Users/jonno/workspace/c302/research/figures/01_network_topology.png"
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"Saved: {out}")

out_svg = "/Users/jonno/workspace/c302/research/figures/01_network_topology.svg"
fig2, ax2 = plt.subplots(1, 1, figsize=(14, 14))
# Re-run for SVG would duplicate code; just note PNG is primary
print(f"PNG saved. SVG generation skipped (re-run with svg backend if needed).")
plt.close()
