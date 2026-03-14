"""Abstract base class for all c302 controllers."""

from abc import ABC, abstractmethod

from worm_bridge.types import WormState, TickRequest, ControlSurface, NeuronGroupActivity


class BaseController(ABC):
    """Base class for all c302 controllers."""

    @abstractmethod
    def tick(self, request: TickRequest) -> tuple[ControlSurface, WormState]:
        """Process one tick. Returns (surface, state)."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset controller to initial state."""
        ...

    @abstractmethod
    def state(self) -> WormState:
        """Return current internal state."""
        ...

    @property
    @abstractmethod
    def controller_type(self) -> str:
        """Return controller type identifier."""
        ...

    def neuron_activity(self) -> NeuronGroupActivity | None:
        """Return neuron activity if available. Override in connectome controllers."""
        return None
