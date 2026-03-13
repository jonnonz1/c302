"""
Pydantic models for the worm-bridge controller service.

Defines the data contracts between the TypeScript agent and the Python
controller. These models mirror the TypeScript interfaces in agent/src/types.ts
and are the source of truth for request/response validation.

Models:
    AgentMode           -- The 7 behavioral modes the controller can select.
    ToolName            -- The 5 tools available to the LLM agent.
    WormState           -- The controller's 6 internal state variables.
    TickSignals         -- Observable coding outcomes sent from agent to controller.
    TickRequest         -- Wrapper: reward + signals.
    NeuronGroupActivity -- Neural activity readings by functional class (Phase 2+).
    ControlSurface      -- The behavioral control surface emitted each tick.
    TickResponse        -- Wrapper: surface + state + optional neuron_activity.

Dependencies: pydantic, typing, enum
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AgentMode(str, Enum):
    """The 7 behavioral modes the controller can select.

    Each mode maps to a distinct system prompt and tool mask on the
    TypeScript agent side.
    """

    DIAGNOSE = "diagnose"
    SEARCH = "search"
    EDIT_SMALL = "edit-small"
    EDIT_LARGE = "edit-large"
    RUN_TESTS = "run-tests"
    REFLECT = "reflect"
    STOP = "stop"


class ToolName(str, Enum):
    """Tools available to the LLM agent.

    The controller restricts which subset is available on each tick
    via the allowed_tools field on ControlSurface.
    """

    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    SEARCH = "search"
    RUN_COMMAND = "run_command"
    LIST_FILES = "list_files"


TOOL_MASKS: dict[AgentMode, list[ToolName]] = {
    AgentMode.DIAGNOSE: [ToolName.READ_FILE, ToolName.SEARCH, ToolName.LIST_FILES],
    AgentMode.SEARCH: [ToolName.READ_FILE, ToolName.SEARCH, ToolName.LIST_FILES],
    AgentMode.EDIT_SMALL: [ToolName.READ_FILE, ToolName.WRITE_FILE, ToolName.LIST_FILES],
    AgentMode.EDIT_LARGE: [
        ToolName.READ_FILE, ToolName.WRITE_FILE, ToolName.SEARCH, ToolName.LIST_FILES,
    ],
    AgentMode.RUN_TESTS: [ToolName.RUN_COMMAND],
    AgentMode.REFLECT: [ToolName.READ_FILE, ToolName.LIST_FILES],
    AgentMode.STOP: [],
}


class WormState(BaseModel):
    """The 6 internal state variables maintained by the controller.

    All floats are bounded. These values are engineered analogies to
    C. elegans neural circuit functions. The same structure is used
    across all controller variants.
    """

    model_config = {"json_schema_extra": {"examples": [
        {
            "arousal": 0.5,
            "novelty_seek": 0.5,
            "stability": 0.5,
            "persistence": 0.5,
            "error_aversion": 0.0,
            "reward_trace": 0.0,
        }
    ]}}

    arousal: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Scales responsiveness to inputs",
    )
    novelty_seek: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Exploration/exploitation balance",
    )
    stability: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Behavioral inertia -- smooths state changes",
    )
    persistence: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Tendency to stay in the current mode",
    )
    error_aversion: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Dampens aggression after negative outcomes",
    )
    reward_trace: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="Exponentially decaying average of recent rewards",
    )


class TickSignals(BaseModel):
    """Observable environment signals sent to the controller each tick.

    These are the controller's only view of the outside world.
    No source code, prompts, or LLM output is exposed.
    """

    error_count: int = Field(
        ge=0,
        description="Number of TypeScript/lint errors in the project",
    )
    test_pass_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of tests currently passing",
    )
    files_changed: int = Field(
        ge=0,
        description="Number of files modified in the last agent action",
    )
    iterations: int = Field(
        ge=0,
        description="Total ticks elapsed so far in this experiment run",
    )
    last_action_type: Optional[ToolName] = Field(
        default=None,
        description="Type of the last tool the agent called",
    )


class TickRequest(BaseModel):
    """Inbound request from the TypeScript agent at the start of each tick.

    Contains the reward from the previous tick (null on the first tick)
    and current observable signals.
    """

    reward: Optional[float] = Field(
        default=None,
        description="Scalar reward from the previous tick",
    )
    signals: TickSignals


class NeuronGroupActivity(BaseModel):
    """Grouped neural activity readings from c302 simulation or replay.

    Keys are neuron names, values are normalized membrane potentials
    in [0, 1]. Present only for connectome controllers.
    """

    sensory: dict[str, float] = Field(
        default_factory=dict,
        description="Sensory neuron activities (e.g. ASEL, ASER, AWCL)",
    )
    command: dict[str, float] = Field(
        default_factory=dict,
        description="Command interneuron activities (e.g. AVA, AVB, PVC)",
    )
    motor: dict[str, float] = Field(
        default_factory=dict,
        description="Motor neuron group activities (e.g. forward, reverse)",
    )


class ControlSurface(BaseModel):
    """The behavioral control surface emitted by the controller.

    This is the sole output interface. The surface applicator on the
    TypeScript side translates these parameters into Claude API
    configuration and prompt construction.
    """

    mode: AgentMode = Field(
        description="The behavioral mode for this tick",
    )
    temperature: float = Field(
        ge=0.2, le=0.8,
        description="LLM sampling temperature",
    )
    token_budget: int = Field(
        ge=500, le=4000,
        description="Maximum tokens for the LLM response",
    )
    search_breadth: int = Field(
        ge=1, le=10,
        description="Number of parallel search paths to explore",
    )
    aggression: float = Field(
        ge=0.0, le=1.0,
        description="Willingness to make large, risky changes",
    )
    stop_threshold: float = Field(
        ge=0.3, le=0.8,
        description="Confidence threshold to trigger stop mode",
    )
    allowed_tools: list[ToolName] = Field(
        description="Tools the agent may use this tick",
    )
    neuron_activity: Optional[NeuronGroupActivity] = Field(
        default=None,
        description="Neural activity readings (connectome controllers only)",
    )


class TickResponse(BaseModel):
    """Response from the controller to the TypeScript agent.

    Contains the control surface for this tick and the controller's
    internal state (for research logging).
    """

    surface: ControlSurface = Field(
        description="The behavioral control surface for this tick",
    )
    state: WormState = Field(
        description="The controller's internal state after this tick",
    )
