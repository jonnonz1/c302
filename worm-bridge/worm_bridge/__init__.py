"""
worm-bridge: C. elegans connectome-derived behavioral controller for c302.

Exposes a FastAPI service that receives coding agent tick signals and reward,
updates internal controller state, and returns a behavioral ControlSurface.

Phase 0: Types and health endpoint only.
"""

__version__ = "0.1.0"
