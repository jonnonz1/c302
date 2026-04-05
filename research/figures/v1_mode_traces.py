#!/usr/bin/env python3
"""
V1 Mode Trace Comparison — the money shot.

Three horizontal timeline strips showing mode-over-ticks for three controllers
on the same Level 2 task. Same mode derivation rules, different neural substrates,
completely different behaviour.
"""

import json
import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
import _font_setup  # noqa: F401 — registers Inter + JetBrains Mono
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

DARK_BG = "#0d1117"
TEXT_COLOR = "#c9d1d9"
SUBTLE_TEXT = "#8b949e"
GRID_COLOR = "#21262d"
ACCENT_BLUE = "#58a6ff"

MODE_COLORS = {
    "reflect":    "#6C8EBF",  # slate blue
    "diagnose":   "#82B366",  # sage green
    "search":     "#D6B656",  # amber
    "edit-small": "#E07C3E",  # orange
    "edit-large": "#CC4125",  # red-orange
    "run-tests":  "#9673A6",  # purple
    "stop":       "#B85450",  # muted red
}

# Text color for readability on each mode background
MODE_TEXT_DARK = {"reflect", "search", "diagnose"}  # dark text on light bg

DATA_DIR = Path("/Users/jonno/workspace/c302/research/experiments")
OUT_DIR = Path("/Users/jonno/workspace/c302/research/figures")

# ── Data sources (curated selections) ─────────────────────────────────────────

TRACES = [
    {
        "label": "Synthetic",
        "sublabel": "random weights, no topology",
        "path": DATA_DIR / "synthetic-battery-20260330-173351-01" / "control-surface-traces.json",
        "outcome": "completed (10 ticks)",
        "outcome_color": "#3fb950",  # green — success
    },
    {
        "label": "Connectome",
        "sublabel": "C. elegans wiring, frozen",
        "path": DATA_DIR / "connectome-battery-20260404-212605-01" / "control-surface-traces.json",
        "outcome": "stalled (9 ticks)",
        "outcome_color": "#f85149",  # red — failure
    },
    {
        "label": "Live",
        "sublabel": "C. elegans wiring, dynamic",
        "path": DATA_DIR / "live-battery-20260403-224824-05" / "control-surface-traces.json",
        "outcome": "29/30 tests (17 ticks)",
        "outcome_color": "#d29922",  # amber — partial
    },
]


def load_modes(path):
    """Load trace JSON and extract mode sequence."""
    with open(path) as f:
        data = json.load(f)
    return [tick["mode"] for tick in data]


def find_runs(modes):
    """Return list of (start, length, mode) tuples for consecutive runs."""
    if not modes:
        return []
    runs = []
    start = 0
    for i in range(1, len(modes)):
        if modes[i] != modes[start]:
            runs.append((start, i - start, modes[start]))
            start = i
    runs.append((start, len(modes) - start, modes[start]))
    return runs


def draw_mode_strip(ax, modes, y_center, bar_height, max_ticks):
    """Draw a single horizontal mode strip as abutting colored rectangles with labels."""
    runs = find_runs(modes)

    for start, length, mode in runs:
        color = MODE_COLORS.get(mode, "#555555")
        # Draw each tick as a separate rounded rect for clean edges
        for j in range(length):
            tick_idx = start + j
            rect = FancyBboxPatch(
                (tick_idx, y_center - bar_height / 2),
                1, bar_height,
                boxstyle="round,pad=0,rounding_size=0.06",
                facecolor=color,
                edgecolor=DARK_BG,
                linewidth=1.8,
                zorder=2,
            )
            ax.add_patch(rect)

        # Label in the center of each run
        mid_x = start + length / 2.0
        text_color = "#1c2128" if mode in MODE_TEXT_DARK else "#ffffff"

        # Short labels for narrow segments
        SHORT = {
            "reflect": "refl",
            "diagnose": "diag",
            "search": "srch",
            "edit-small": "edit",
            "edit-large": "EDIT",
            "run-tests": "test",
            "stop": "stop",
        }
        if length >= 3:
            label = mode
            fontsize = 9.5
        elif length == 2:
            label = SHORT.get(mode, mode[:4])
            fontsize = 8.5
        else:
            label = SHORT.get(mode, mode[:4])
            fontsize = 7.5

        ax.text(
            mid_x, y_center, label,
            ha="center", va="center",
            fontsize=fontsize, fontweight="bold",
            color=text_color,
            alpha=0.92,
            zorder=3,
        )


def main():
    # ── Load data ──────────────────────────────────────────────────────────
    all_modes = []
    for trace in TRACES:
        modes = load_modes(trace["path"])
        all_modes.append(modes)
        print(f"{trace['label']:12s}  {len(modes):2d} ticks  {modes}")

    max_ticks = max(len(m) for m in all_modes)

    # ── Create figure ──────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(16, 6), dpi=300)
    fig.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)

    # Layout: 3 strips stacked with generous spacing
    bar_height = 0.65
    strip_spacing = 1.5
    y_positions = [strip_spacing * (2 - i) for i in range(3)]
    # y_positions: [3.0, 1.5, 0.0] top to bottom

    for i, (trace, modes) in enumerate(zip(TRACES, all_modes)):
        y = y_positions[i]
        draw_mode_strip(ax, modes, y, bar_height, max_ticks)

        # Controller label (left side) — two lines
        ax.text(
            -0.6, y + 0.12, trace["label"],
            ha="right", va="center",
            fontsize=17, fontweight="bold",
            color=TEXT_COLOR,
        )
        ax.text(
            -0.6, y - 0.22, trace["sublabel"],
            ha="right", va="center",
            fontsize=9,
            color=SUBTLE_TEXT,
            style="italic",
        )

        # Outcome label (right side) — color-coded
        n_ticks = len(modes)
        ax.text(
            n_ticks + 0.5, y, trace["outcome"],
            ha="left", va="center",
            fontsize=9.5,
            color=trace["outcome_color"],
            fontweight="medium",
        )

    # ── Annotations ────────────────────────────────────────────────────────

    # Synthetic: "task completed" arrow at the end
    y_syn = y_positions[0]
    n_syn = len(all_modes[0])
    ax.annotate(
        "task completed",
        xy=(n_syn - 0.05, y_syn),
        xytext=(n_syn + 0.4, y_syn + 0.55),
        fontsize=9.5, color="#3fb950",
        ha="left", va="center",
        fontweight="bold",
        arrowprops=dict(arrowstyle="-|>", color="#3fb950", lw=1.5),
        zorder=5,
    )

    # Connectome: "never writes code" — arrow points at end of trace
    y_con = y_positions[1]
    n_con = len(all_modes[1])
    ax.annotate(
        "never writes code",
        xy=(n_con - 0.5, y_con + bar_height / 2 + 0.02),
        xytext=(n_con + 1.5, y_con + 0.65),
        fontsize=9.5, color="#f85149",
        ha="center", va="center",
        fontweight="bold",
        arrowprops=dict(arrowstyle="-|>", color="#f85149", lw=1.5),
        zorder=5,
    )

    # Live: "fixes 3 tests" annotation near the run-tests tick (tick 1)
    y_live = y_positions[2]
    ax.annotate(
        "fixes 3 tests (26 \u2192 29 / 30)",
        xy=(1.5, y_live + bar_height / 2 + 0.02),
        xytext=(4.0, y_live + 0.72),
        fontsize=9, color=ACCENT_BLUE,
        ha="center", va="center",
        fontweight="bold",
        arrowprops=dict(
            arrowstyle="-|>",
            color=ACCENT_BLUE,
            lw=1.5,
            connectionstyle="arc3,rad=-0.15",
        ),
        zorder=5,
    )

    # ── Axes formatting ────────────────────────────────────────────────────
    ax.set_xlim(-0.3, max_ticks + 0.3)
    ax.set_ylim(
        y_positions[-1] - bar_height - 0.15,
        y_positions[0] + bar_height + 0.9,
    )

    # X-axis: tick numbers at segment centers
    tick_positions = [i + 0.5 for i in range(max_ticks)]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(
        [str(i) for i in range(max_ticks)],
        fontsize=9, color=SUBTLE_TEXT,
    )
    ax.tick_params(axis="x", length=0, pad=8)
    ax.set_xlabel("Tick", fontsize=11, color=TEXT_COLOR, labelpad=10)

    # Remove y-axis
    ax.set_yticks([])
    ax.yaxis.set_visible(False)

    # Spine styling
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Subtle vertical grid lines at tick boundaries
    for tick in range(max_ticks + 1):
        ax.axvline(x=tick, color=GRID_COLOR, linewidth=0.5, zorder=0)

    # ── Title ──────────────────────────────────────────────────────────────
    ax.text(
        0.0, 1.07,
        "Mode sequences \u2014 Level 2",
        transform=ax.transAxes,
        fontsize=16, fontweight="bold",
        color=TEXT_COLOR,
        ha="left", va="bottom",
    )
    ax.text(
        0.0, 1.025,
        "same derivation rules, different substrates",
        transform=ax.transAxes,
        fontsize=11,
        color=SUBTLE_TEXT,
        ha="left", va="bottom",
        style="italic",
    )

    # ── Legend ──────────────────────────────────────────────────────────────
    used_modes = set()
    for modes in all_modes:
        used_modes.update(modes)

    mode_order = ["reflect", "diagnose", "search", "edit-small", "edit-large", "run-tests", "stop"]
    legend_handles = []
    for mode in mode_order:
        if mode in used_modes:
            patch = mpatches.Patch(
                facecolor=MODE_COLORS[mode],
                edgecolor="none",
                label=mode,
            )
            legend_handles.append(patch)

    ax.legend(
        handles=legend_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=len(legend_handles),
        frameon=False,
        fontsize=10.5,
        handlelength=2.0,
        handleheight=1.3,
        labelcolor=TEXT_COLOR,
        columnspacing=2.5,
    )

    # ── Save ───────────────────────────────────────────────────────────────
    out_path = OUT_DIR / "v1_mode_traces.png"
    fig.savefig(out_path, dpi=300, facecolor=DARK_BG, bbox_inches="tight", pad_inches=0.5)
    plt.close(fig)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
