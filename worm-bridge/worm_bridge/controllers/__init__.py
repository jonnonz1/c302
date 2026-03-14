"""Controller package. Provides factory for creating controllers by type."""

from worm_bridge.controllers.base import BaseController
from worm_bridge.controllers.random_controller import RandomController
from worm_bridge.controllers.static import StaticController
from worm_bridge.controllers.synthetic import SyntheticController

_REGISTRY: dict[str, type[BaseController]] = {
    "static": StaticController,
    "synthetic": SyntheticController,
    "random": RandomController,
}


def create_controller(controller_type: str) -> BaseController:
    """Create a controller by type name.

    Args:
        controller_type: One of "static", "synthetic", "random".

    Raises:
        ValueError: If controller_type is not registered.
    """
    cls = _REGISTRY.get(controller_type)
    if cls is None:
        raise ValueError(
            f"Unknown controller type: {controller_type!r}. "
            f"Available: {list(_REGISTRY.keys())}"
        )
    return cls()


__all__ = [
    "BaseController",
    "RandomController",
    "StaticController",
    "SyntheticController",
    "create_controller",
]
