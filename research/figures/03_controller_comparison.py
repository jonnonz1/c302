#!/usr/bin/env python3
"""Controller Comparison Bar Chart.

Shows success rates across 4 controllers (static, random, synthetic, connectome)
for Phase 1 (Level 1, Level 2) and Phase 2 (Level 1), with confidence intervals.

Data from battery results in project_battery_results.md.
"""

import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


# ---------- Data from battery results ----------

# Phase 1 results (budget-derived iterations, 212 runs total)
# Level 1: 15 runs per controller, Level 2: ~15 runs per controller
phase1_data = {
    "Level 1 (Phase 1)": {
        "Static":     {"n": 15, "success": 15},   # 100%
        "Random":     {"n": 15, "success": 13.5},  # 90%
        "Synthetic":  {"n": 15, "success": 15},   # 100%
        "Connectome": {"n": 0,  "success": 0},    # Not tested in Phase 1
    },
    "Level 2 (Phase 1)": {
        "Static":     {"n": 15, "success": 0},    # 0%
        "Random":     {"n": 15, "success": 1.8},  # 12%
        "Synthetic":  {"n": 15, "success": 1.05}, # 7%
        "Connectome": {"n": 0,  "success": 0},    # Not tested
    },
}

# Phase 2 results (fixed 6 iterations, 60 runs)
phase2_data = {
    "Level 1 (Phase 2)": {
        "Static":     {"n": 15, "success": 15},   # 100%
        "Random":     {"n": 15, "success": 15},   # 100%
        "Synthetic":  {"n": 15, "success": 15},   # 100%
        "Connectome": {"n": 15, "success": 10},   # 67%
    },
}


def wilson_ci(successes, n, z=1.96):
    """Wilson score confidence interval for a proportion."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    lo = max(0, center - spread)
    hi = min(1, center + spread)
    return p, lo, hi


# ---------- Build figure ----------

fig, axes = plt.subplots(1, 3, figsize=(18, 7), sharey=True)
fig.patch.set_facecolor("#0F172A")

controllers = ["Static", "Random", "Synthetic", "Connectome"]
bar_colors = ["#64748B", "#A78BFA", "#34D399", "#F59E0B"]
edge_colors = ["#94A3B8", "#C4B5FD", "#6EE7B7", "#FCD34D"]

datasets = [
    ("Level 1 (Phase 1)", phase1_data["Level 1 (Phase 1)"]),
    ("Level 2 (Phase 1)", phase1_data["Level 2 (Phase 1)"]),
    ("Level 1 (Phase 2)", phase2_data["Level 1 (Phase 2)"]),
]

for idx, (title, data) in enumerate(datasets):
    ax = axes[idx]
    ax.set_facecolor("#1E293B")

    rates = []
    errors_lo = []
    errors_hi = []
    bar_cols = []
    edge_cols = []
    labels = []

    for i, ctrl in enumerate(controllers):
        d = data[ctrl]
        if d["n"] == 0:
            # Controller not tested at this level
            rates.append(0)
            errors_lo.append(0)
            errors_hi.append(0)
            bar_cols.append("#334155")
            edge_cols.append("#475569")
            labels.append(f"{ctrl}\n(N/A)")
        else:
            p, lo, hi = wilson_ci(d["success"], d["n"])
            rates.append(p * 100)
            errors_lo.append((p - lo) * 100)
            errors_hi.append((hi - p) * 100)
            bar_cols.append(bar_colors[i])
            edge_cols.append(edge_colors[i])
            pct = f"{p * 100:.0f}%"
            labels.append(f"{ctrl}\n(n={d['n']})")

    x = np.arange(len(controllers))
    bars = ax.bar(x, rates, width=0.65, color=bar_cols, edgecolor=edge_cols,
                  linewidth=1.5, zorder=3)

    # Error bars
    valid = [i for i in range(len(controllers)) if data[controllers[i]]["n"] > 0]
    if valid:
        ax.errorbar(
            [x[i] for i in valid],
            [rates[i] for i in valid],
            yerr=[[errors_lo[i] for i in valid], [errors_hi[i] for i in valid]],
            fmt="none", ecolor="#E2E8F0", elinewidth=1.5, capsize=5, capthick=1.5,
            zorder=4,
        )

    # Value labels on bars
    for i, bar in enumerate(bars):
        if data[controllers[i]]["n"] > 0:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 3,
                    f"{h:.0f}%", ha="center", va="bottom",
                    fontsize=13, fontweight="bold", color="white")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9, color="#CBD5E1")
    ax.set_title(title, fontsize=14, fontweight="bold", color="white", pad=12)
    ax.set_ylim(0, 115)

    # Grid
    ax.yaxis.grid(True, color="#334155", linewidth=0.5, alpha=0.5)
    ax.set_axisbelow(True)

    for spine in ax.spines.values():
        spine.set_color("#334155")
    ax.tick_params(colors="#94A3B8")

axes[0].set_ylabel("Success Rate (%)", fontsize=12, color="#CBD5E1", labelpad=8)

# Phase labels
fig.text(0.28, 0.02, "Phase 1: Budget-derived iterations (212 runs)",
         ha="center", fontsize=9, color="#64748B", style="italic")
fig.text(0.78, 0.02, "Phase 2: Fixed 6 iterations (60 runs)",
         ha="center", fontsize=9, color="#64748B", style="italic")

# Divider
axes[1].axvline(x=3.8, color="#475569", linewidth=2, linestyle="--", alpha=0.5,
                clip_on=False)

fig.suptitle("Controller Success Rates Across Difficulty Levels",
             fontsize=18, fontweight="bold", color="white", y=0.98)

# Key finding annotation
fig.text(0.5, 0.93,
         "332 total experiment runs  |  4 controllers  |  C. elegans c302 connectome",
         ha="center", fontsize=10, color="#94A3B8")

plt.tight_layout(rect=[0, 0.05, 1, 0.90])

out = "/Users/jonno/workspace/c302/research/figures/03_controller_comparison.png"
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"Saved: {out}")
