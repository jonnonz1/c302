"""
V3 Results Summary — Heatmap of task completion rates across controllers and difficulty levels.
392 experiments total (n=15 per cell).
"""

import sys; sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
import _font_setup  # noqa: F401 — registers Inter + JetBrains Mono
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import numpy as np

# ── Data ──────────────────────────────────────────────────────────────────────
controllers = [
    "Static",
    "Random",
    "Synthetic",
    None,                     # divider row (invisible)
    "Connectome\n(pre-fix)",
    "Connectome\n(post-fix)",
    "Live",
]

level1 = [100, 100, 100, None, 67, 100, 100]
level2 = [13,  13,  20,  None, 0,  0,   0]

fractions_l1 = ["15/15", "15/15", "15/15", "", "10/15", "15/15", "15/15"]
fractions_l2 = ["2/15",  "2/15",  "3/15",  "", "0/15",  "0/15",  "0/15"]

# ── Color scale: dark red -> amber -> green ───────────────────────────────────
cmap = mcolors.LinearSegmentedColormap.from_list(
    "red_amber_green",
    [
        (0.00, "#8b1a1a"),
        (0.25, "#c0392b"),
        (0.50, "#d4a017"),
        (0.75, "#73a942"),
        (1.00, "#27ae60"),
    ],
)

# ── Layout constants ─────────────────────────────────────────────────────────
BG      = "#0d1117"
TEXT    = "#c9d1d9"
SUBTLE  = "#8b949e"
DIVIDER_COLOR = "#30363d"

CELL_W = 3.8        # wide cells so text fits
CELL_H = 0.85       # row height
GAP_COL = 0.25      # gap between the two columns
DIVIDER_GAP = 0.35  # extra vertical space for the divider row

# X positions for the two columns
col_x = [0.0, CELL_W + GAP_COL]
grid_right = col_x[1] + CELL_W
grid_cx = grid_right / 2.0  # horizontal center of the grid

# Build Y positions bottom-up, skipping the divider row with a gap
# Row order top-to-bottom: Static(0), Random(1), Synthetic(2), --div--, ConnPre(4), ConnPost(5), Live(6)
# We draw bottom-up so Live is at the bottom.
real_rows = [i for i in range(len(controllers)) if controllers[i] is not None]
n_real = len(real_rows)

row_y = {}
y = 0.0
for idx in reversed(real_rows):
    row_y[idx] = y
    y += CELL_H
    # After row 4 (Connectome pre-fix), add the divider gap
    if idx == 4:
        y += DIVIDER_GAP

grid_top = y
grid_bottom = 0.0

# ── Figure ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG)
ax.set_facecolor(BG)

# Draw cells
for row_idx in real_rows:
    vals = [level1[row_idx], level2[row_idx]]
    fracs = [fractions_l1[row_idx], fractions_l2[row_idx]]
    by = row_y[row_idx]

    for col in range(2):
        val = vals[col]
        frac = fracs[col]
        bx = col_x[col]

        color = cmap(val / 100.0)

        # Rounded rectangle
        rect = mpatches.FancyBboxPatch(
            (bx, by), CELL_W, CELL_H,
            boxstyle=mpatches.BoxStyle.Round(pad=0.0, rounding_size=0.08),
            facecolor=color,
            edgecolor=BG,
            linewidth=4,
        )
        ax.add_patch(rect)

        # Decide text color based on background luminance
        r_c, g_c, b_c = mcolors.to_rgb(color)
        lum = 0.299 * r_c + 0.587 * g_c + 0.114 * b_c
        txt_color = "#ffffff" if lum < 0.45 else "#1a1a2e"

        cx = bx + CELL_W / 2
        cy = by + CELL_H / 2

        pct = int(val)

        # Percentage -- large bold
        ax.text(
            cx, cy + CELL_H * 0.12,
            f"{pct}%",
            ha="center", va="center",
            fontsize=28, fontweight="bold",
            color=txt_color,
            fontfamily="sans-serif",
        )
        # Fraction -- smaller, below
        ax.text(
            cx, cy - CELL_H * 0.22,
            frac,
            ha="center", va="center",
            fontsize=14,
            color=txt_color,
            alpha=(0.85 if pct > 0 else 0.55),
            fontfamily="sans-serif",
        )

# ── Divider line ──────────────────────────────────────────────────────────────
div_y = row_y[4] + CELL_H + DIVIDER_GAP / 2
ax.plot(
    [col_x[0] - 0.1, grid_right + 0.1], [div_y, div_y],
    color=DIVIDER_COLOR, linewidth=1.2, linestyle="--",
)

# ── Group labels (right side, rotated) ────────────────────────────────────────
label_x = grid_right + 0.45

# Baselines: rows 0,1,2
baseline_mid_y = (row_y[0] + CELL_H + row_y[2]) / 2
ax.text(
    label_x, baseline_mid_y,
    "Baselines",
    ha="center", va="center",
    fontsize=13, color=SUBTLE, fontstyle="italic",
    fontfamily="sans-serif",
    rotation=270,
)

# Bio-inspired: rows 4,5,6
bio_mid_y = (row_y[4] + CELL_H + row_y[6]) / 2
ax.text(
    label_x, bio_mid_y,
    "Bio-inspired",
    ha="center", va="center",
    fontsize=13, color=SUBTLE, fontstyle="italic",
    fontfamily="sans-serif",
    rotation=270,
)

# ── Row labels (left side) ───────────────────────────────────────────────────
for row_idx in real_rows:
    ax.text(
        col_x[0] - 0.25,
        row_y[row_idx] + CELL_H / 2,
        controllers[row_idx],
        ha="right", va="center",
        fontsize=16, fontweight="bold",
        color=TEXT,
        fontfamily="sans-serif",
    )

# ── Column headers ───────────────────────────────────────────────────────────
header_y = grid_top + 0.25
for col, label in enumerate(["Level 1", "Level 2"]):
    ax.text(
        col_x[col] + CELL_W / 2,
        header_y,
        label,
        ha="center", va="bottom",
        fontsize=22, fontweight="bold",
        color=TEXT,
        fontfamily="sans-serif",
    )

# ── Title ─────────────────────────────────────────────────────────────────────
ax.text(
    grid_cx, header_y + 1.2,
    "Task completion rates \u2014 392 experiments (n=15 per cell)",
    ha="center", va="bottom",
    fontsize=24, fontweight="bold",
    color="#ffffff",
    fontfamily="sans-serif",
)

# ── Subtitle ──────────────────────────────────────────────────────────────────
ax.text(
    grid_cx, header_y + 0.5,
    "Level 1: add priority field (3 files)   |   Level 2: fix regression without breaking tests",
    ha="center", va="bottom",
    fontsize=14,
    color=SUBTLE,
    fontfamily="sans-serif",
)

# ── Axes cleanup ──────────────────────────────────────────────────────────────
ax.set_xlim(-3.0, grid_right + 1.2)
ax.set_ylim(-0.5, header_y + 2.0)
ax.set_aspect("auto")
ax.axis("off")

plt.savefig(
    "/Users/jonno/workspace/c302/research/figures/v3_results_heatmap.png",
    dpi=300,
    facecolor=BG,
    bbox_inches="tight",
    pad_inches=0.5,
)
plt.close()
print("Saved v3_results_heatmap.png")
