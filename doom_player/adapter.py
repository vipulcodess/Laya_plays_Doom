"""Model adapter boundary. No LAYA runtime or protocol is assumed here."""

from importlib import import_module
from typing import Any, Callable, Dict, Protocol


class DecisionProvider(Protocol):
    def decide(self, observation: Dict[str, Any]) -> Any:
        """Return a JSON-compatible decision. See README for the adapter contract."""


def load_provider(spec: str, model_id: str = "") -> DecisionProvider:
    """Load an adapter factory written by the user as ``module:factory``."""
    if ":" not in spec:
        raise ValueError("adapter must be specified as python.module:factory")
    module_name, factory_name = spec.split(":", 1)
    if not module_name or not factory_name:
        raise ValueError("adapter must be specified as python.module:factory")
    factory: Callable[..., Any] = getattr(import_module(module_name), factory_name)
    provider = factory(model_id=model_id)
    if not callable(getattr(provider, "decide", None)):
        raise TypeError("adapter factory must return an object with decide(observation)")
    return provider
