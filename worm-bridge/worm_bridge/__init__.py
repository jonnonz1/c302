"""worm-bridge: C. elegans connectome-derived behavioral controller for c302.

Exposes a FastAPI service that receives coding agent tick signals and reward,
updates internal controller state, and returns a behavioral ControlSurface.

The bridge sits between the c302 neural simulation and the LLM coding agent,
translating neural dynamics into agent configuration parameters.

Modules:
    types  -- Pydantic models for the controller API contract
    server -- FastAPI application with controller endpoints

Phase 0: Static controller with fixed mode cycle and constant parameters.
"""

__version__ = "0.1.0"
