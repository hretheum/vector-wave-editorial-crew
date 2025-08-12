"""
Compat shims for legacy CrewAI flow decorators and base classes.

Goal: allow import-time compatibility for old tests without executing legacy flows.
These are no-op implementations to prevent NameError during test collection.
"""
from typing import TypeVar, Generic, Callable, Any

T = TypeVar("T")


def start(*args: Any, **kwargs: Any):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    # Support both @start and @start()
    if args and callable(args[0]) and not kwargs:
        return args[0]
    return decorator


def flow_listen(*_args: Any, **_kwargs: Any):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    return decorator


class Flow(Generic[T]):
    """Minimal generic base to satisfy class inheritance in legacy tests."""

    pass
