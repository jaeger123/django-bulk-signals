"""Helpers for binding one handler to several signals at once."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from django.dispatch import receiver

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.db import models
    from django.dispatch import Signal

__all__ = ["apply_signals"]

F = TypeVar("F", bound="Callable[..., object]")


def apply_signals(model: type[models.Model], *signals: Signal) -> Callable[[F], F]:
    """Connect one handler to several signals for a single model.

    Args:
        model: The model to use as the signals' ``sender``.
        signals: The signals to connect the decorated function to.

    Returns:
        A decorator that registers the function and returns it unchanged.

    Example:
        >>> @apply_signals(Customer, pre_bulk_update, pre_update)
        ... def handler(sender, **kwargs): ...

    """

    def decorator(func: F) -> F:
        for signal in signals:
            receiver(signal, sender=model)(func)
        return func

    return decorator
