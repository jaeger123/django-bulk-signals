"""Shared pytest fixtures for the django_bulk_signals suite."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType

    from django.dispatch import Signal


class Recorder:
    """Capture every payload a signal receives."""

    def __init__(self, signal: Signal, sender: type | None = None) -> None:
        """Record `signal`, optionally narrowed to one `sender`."""
        self.signal = signal
        self.sender = sender
        self.calls: list[dict[str, Any]] = []

    def connect(self) -> None:
        """Start listening."""
        self.signal.connect(self._handler, sender=self.sender, weak=False)

    def disconnect(self) -> None:
        """Stop listening."""
        self.signal.disconnect(self._handler, sender=self.sender)

    def _handler(self, sender: type, **kwargs: object) -> None:  # noqa: ARG002
        self.calls.append(kwargs)

    @property
    def count(self) -> int:
        """How many times the signal fired."""
        return len(self.calls)

    def changed_fields(self, index: int = 0) -> dict[Any, dict[str, Any]]:
        """Map primary key -> changed fields, from one recorded payload."""
        forward_data = self.calls[index].get("forward_data") or {}
        return {
            obj["object"].pk: obj["fields"] for obj in forward_data.get("objects", [])
        }


@pytest.fixture
def record() -> Iterator[Any]:
    """Return a factory that records a signal and disconnects afterwards."""
    recorders: list[Recorder] = []

    def _record(signal: Signal, sender: type | None = None) -> Recorder:
        recorder = Recorder(signal, sender)
        recorder.connect()
        recorders.append(recorder)
        return recorder

    yield _record

    for recorder in recorders:
        recorder.disconnect()


@pytest.fixture
def signals() -> ModuleType:
    """Return the package's signals module.

    Imported lazily because the package does not import at all on Django >= 4.0
    (KNOWN BUG #1); modules that use this fixture are skipped in that case.
    """
    from django_bulk_signals import signals as signals_module

    return signals_module
