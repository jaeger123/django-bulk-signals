"""Signals for Django's bulk queryset operations, with field-level diffing.

Django emits no signals for ``bulk_create()``, ``bulk_update()`` or
``QuerySet.update()`` - still true as of Django 6.1. This package adds them,
along with a description of exactly which fields changed on which instances.
"""

from django_bulk_signals.decorators import apply_signals
from django_bulk_signals.managers import CustomManager, MyModelQuerySet
from django_bulk_signals.signals import (
    post_bulk_create,
    post_bulk_update,
    pre_bulk_create,
    pre_bulk_update,
    pre_update,
)
from django_bulk_signals.utils import (
    find_specific_updated_values,
    find_updated_values,
)

__all__ = [
    "CustomManager",
    "MyModelQuerySet",
    "apply_signals",
    "find_specific_updated_values",
    "find_updated_values",
    "post_bulk_create",
    "post_bulk_update",
    "pre_bulk_create",
    "pre_bulk_update",
    "pre_update",
]
