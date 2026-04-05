#!/usr/bin/env python3
"""
V6 Tick Comparison — The Stop Mechanism

Horizontal stacked bar chart showing productive ticks vs post-solve waste
for each controller at Level 1. Makes the cost of not knowing when to stop
visually obvious.
"""

import json
import numpy as np
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
import _font_setup  # noqa: F401 — registers Inter + JetBrains Mono
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

DARK_BG = "#0d1117"
TEXT_COLOR = "#c9d1d9"
SUBTLE_TEXT = "#8b949e"
GRID_COLOR = "#21262d"

# Bar colors
PRODUCTIVE_COLOR = "#2D6A4F"   # dark forest green
WASTE_COLOR = "#6B3A3A"        # muted burgundy/red-grey

DATA_DIR = Path("/Users/jonno/workspace/c302/research/experiments")
OUT_DIR = Path("/Users/jonno/workspace/c302/research/figures")

# ── Load actual solve tick data from experiments ──────────────────────────────

def get_solve_tick(run_dir):
    """Find the first tick where pass_rate >= 0.96 (effectively solved)."""
    path = run_dir / "repo-snapshots.json"
    try:
        with open(path) as f:
            data = json.load(f)
        for tick_idx, snap in enumerate(data):
            if snap["test_results"]["pass_rate"] >= 0.96:
                return tick_idx
        return None
    except FileNotFoundError:
        return None

def get_avg_solve_tick(prefix, n_runs=15):
    """Get average solve tick across battery runs."""
    solve_ticks = []
    for i in range(1, n_runs + 1):
        run_dir = DATA_DIR / f"{prefix}-{i:02d}"
        st = get_solve_tick(run_dir)
        if st is not None:
            solve_ticks.append(st)
    if solve_ticks:
        return sum(solve_ticks) / len(solve_ticks)
    return None

# Compute actual average solve ticks from data
solve_ticks_data = {
    "Static":     get_avg_solve_tick("static-battery-20260330-151123"),
    "Random":     get_avg_solve_tick("random-battery-20260330-162356"),
    "Synthetic":  get_avg_solve_tick("synthetic-battery-20260330-173351"),
    "Connectome": get_avg_solve_tick("connectome-battery-20260404-204954"),
    "Live":       get_avg_solve_tick("live-battery-20260403-141637"),
}

# Print actual solve data for verification
for name, st in solve_ticks_data.items():
    print(f"  {name}: avg solve tick = {st}")

# ── Verified averages (from spec) ────────────────────────────────────────────

# Total ticks per controller (verified)
total_ticks = {
    "Static":     14.7,
    "Random":     11.5,
    "Synthetic":  4.7,
    "Connectome": 6.9,
    "Live":       12.0,
}

# Use computed solve ticks, falling back to reasonable defaults
# Cap productive ticks at total to avoid negative waste
productive_ticks = {}
for name in total_ticks:
    st = solve_ticks_data.get(name)
    if st is not None:
        # Productive = solve tick + 1 (tick is 0-indexed, so tick 2 means 3 ticks of work)
        productive_ticks[name] = min(st + 1, total_ticks[name])
    else:
        productive_ticks[name] = 3  # fallback

# Sort by total ticks descending (most waste first)
sorted_names = sorted(total_ticks.keys(), key=lambda k: total_ticks[k], reverse=True)

# Build bar data
labels = sorted_names
prod = [productive_ticks[n] for n in labels]
waste = [total_ticks[n] - productive_ticks[n] for n in labels]
totals = [total_ticks[n] for n in labels]

# ── Create figure ─────────────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(16, 9), dpi=300, facecolor=DARK_BG)
ax.set_facecolor(DARK_BG)

y_pos = np.arange(len(labels))
bar_height = 0.55

# Draw productive bars
bars_prod = ax.barh(y_pos, prod, height=bar_height, color=PRODUCTIVE_COLOR,
                     edgecolor="none", label="Productive ticks (to solve)", zorder=3)

# Draw waste bars (stacked after productive)
bars_waste = ax.barh(y_pos, waste, height=bar_height, left=prod, color=WASTE_COLOR,
                      edgecolor="none", label="Post-solve waste", zorder=3)

# ── Labels ────────────────────────────────────────────────────────────────────

# Controller names on the left
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=14, fontweight="bold", color=TEXT_COLOR)

# Total tick labels on the right of each bar
for i, (total, p, w) in enumerate(zip(totals, prod, waste)):
    ax.text(total + 0.3, i, f"{total:.1f} ticks",
            va="center", ha="left", fontsize=12, fontweight="bold", color=TEXT_COLOR)
    # Small productive count inside the green section
    if p >= 2:
        ax.text(p / 2, i, f"{p:.0f}",
                va="center", ha="center", fontsize=10, fontweight="bold",
                color="white", alpha=0.8)

# ── Annotations ───────────────────────────────────────────────────────────────

# Find the Synthetic bar index
synth_idx = labels.index("Synthetic")
static_idx = labels.index("Static")
live_idx = labels.index("Live")

# Annotation: Synthetic savings
pct_savings = (1 - total_ticks["Synthetic"] / total_ticks["Static"]) * 100
ax.annotate(
    f"{pct_savings:.0f}% fewer ticks than Static",
    xy=(total_ticks["Synthetic"] + 2.8, synth_idx),
    xytext=(9, synth_idx),
    fontsize=11, fontweight="bold", color="#4ECDC4",
    arrowprops=dict(arrowstyle="-", color="#4ECDC4", lw=1.5),
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#161b22", edgecolor="#4ECDC4",
              linewidth=1, alpha=0.95),
    va="center",
    zorder=10,
)

# Annotation: Live — solves at tick 2, doesn't stop
# Position the text to the right inside the waste zone
waste_mid = prod[live_idx] + waste[live_idx] / 2
ax.annotate(
    "solves at tick 2, doesn't stop",
    xy=(prod[live_idx] + 0.3, live_idx),
    xytext=(prod[live_idx] + 4.5, live_idx - 0.75),
    fontsize=10, fontweight="bold", color="#FF6B6B",
    arrowprops=dict(arrowstyle="->", color="#FF6B6B", lw=1.8,
                    connectionstyle="arc3,rad=-0.15"),
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#161b22", edgecolor="#FF6B6B",
              linewidth=1, alpha=0.95),
    zorder=10,
)

# ── Styling ───────────────────────────────────────────────────────────────────

ax.set_xlim(0, 18)
ax.set_xlabel("Ticks", fontsize=13, color=TEXT_COLOR, labelpad=12)
ax.set_xticks(range(0, 18, 2))
ax.set_xticklabels(range(0, 18, 2), fontsize=10, color=SUBTLE_TEXT)
ax.invert_yaxis()

# Grid — vertical only
ax.grid(True, axis="x", color=GRID_COLOR, linewidth=0.5, alpha=0.6)
ax.grid(False, axis="y")
ax.set_axisbelow(True)

# Spines
for spine in ax.spines.values():
    spine.set_color(GRID_COLOR)
ax.tick_params(colors=SUBTLE_TEXT, length=3, left=False)

# Legend
legend_patches = [
    mpatches.Patch(color=PRODUCTIVE_COLOR, label="Productive ticks (to solve)"),
    mpatches.Patch(color=WASTE_COLOR, label="Post-solve waste"),
]
legend = ax.legend(
    handles=legend_patches,
    loc="lower right",
    fontsize=11,
    frameon=True,
    facecolor="#161b22",
    edgecolor="#30363d",
    labelcolor=TEXT_COLOR,
    borderpad=0.8,
)

# ── Title ─────────────────────────────────────────────────────────────────────

fig.text(0.08, 0.95, "Level 1 \u2014 total ticks per run",
         fontsize=20, fontweight="bold", color=TEXT_COLOR, ha="left")
fig.text(0.08, 0.91, "solve tick ~2 for all controllers",
         fontsize=13, color=SUBTLE_TEXT, ha="left")

# ── Save ──────────────────────────────────────────────────────────────────────

out_path = OUT_DIR / "v6_tick_comparison.png"
fig.savefig(out_path, dpi=300, facecolor=DARK_BG, edgecolor="none",
            bbox_inches="tight", pad_inches=0.3)
plt.close(fig)
print(f"Saved: {out_path}")
