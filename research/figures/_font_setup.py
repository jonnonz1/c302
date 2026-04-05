"""Shared font setup for presentation figures.

Registers Inter and JetBrains Mono from ~/Library/Fonts
and sets Inter as the default font family.

Usage: import _font_setup  (before any matplotlib plotting)
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.font_manager as fm
import os
import glob

# Register user-installed fonts
_font_dir = os.path.expanduser("~/Library/Fonts")
for _f in glob.glob(os.path.join(_font_dir, "*.otf")) + glob.glob(os.path.join(_font_dir, "*.ttf")):
    try:
        fm.fontManager.addfont(_f)
    except Exception:
        pass

# Set Inter as default, JetBrains Mono for monospace
matplotlib.rcParams.update({
    "font.family": "Inter",
    "font.sans-serif": ["Inter", "Helvetica Neue", "Arial", "sans-serif"],
    "font.monospace": ["JetBrains Mono", "Menlo", "Monaco", "monospace"],
    "axes.unicode_minus": False,
})
