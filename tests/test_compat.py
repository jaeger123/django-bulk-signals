"""Characterisation tests for Django-version compatibility.

These lock in the *current* behaviour of the package so that any change to it
is loud rather than silent. When a KNOWN BUG is fixed, the assertion here is
expected to fail - that is the signal to update it.
"""

from __future__ import annotations

import inspect
import warnings

import django
import pytest
from django.db.models.query import QuerySet

from tests.models import IMPORT_ERROR


def test_import_outcome_matches_django_version() -> None:
    """KNOWN BUG #1: Signal(providing_args=...) was removed in Django 4.0.

    django_bulk_signals/signals.py passes providing_args at import time. Django
    3.0 deprecated it (RemovedInDjango40Warning) and 4.0 removed it, so
    importing the package raises TypeError on Django >= 4.0.

    When signals.py drops the argument, the else-branch below will fail.
    Replace this whole test with ``assert IMPORT_ERROR is None``.
    """
    if django.VERSION < (4, 0):
        assert IMPORT_ERROR is None, f"expected a clean import: {IMPORT_ERROR}"
    else:
        assert isinstance(IMPORT_ERROR, TypeError)
        assert "providing_args" in str(IMPORT_ERROR)


@pytest.mark.skipif(django.VERSION >= (4, 0), reason="providing_args no longer exists")
def test_providing_args_is_deprecated_on_django_3() -> None:
    """The removal was announced by a warning we could have caught."""
    from django.dispatch import Signal

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Signal(providing_args=["x"])

    assert any("providing_args" in str(w.message) for w in caught)


def test_bulk_create_upstream_signature() -> None:
    """Track the upstream signature this package overrides."""
    params = set(inspect.signature(QuerySet.bulk_create).parameters)
    expected = {"self", "objs", "batch_size", "ignore_conflicts"}
    if django.VERSION >= (4, 1):
        # Django 4.1 added upsert support.
        expected |= {"update_conflicts", "update_fields", "unique_fields"}
    assert params == expected


def test_bulk_update_upstream_signature() -> None:
    """bulk_update()'s signature is unchanged from Django 3.2 through 6.1."""
    params = set(inspect.signature(QuerySet.bulk_update).parameters)
    assert params == {"self", "objs", "fields", "batch_size"}


@pytest.mark.django_db
def test_stock_django_emits_no_signals_for_bulk_operations() -> None:
    """Why this package exists: Django still has no bulk signals in 6.1."""
    from django.db.models.signals import post_save, pre_save

    from tests.models import Category

    fired: list[object] = []

    def handler(**kwargs: object) -> None:
        fired.append(kwargs["signal"])

    pre_save.connect(handler, weak=False)
    post_save.connect(handler, weak=False)
    try:
        Category.objects.bulk_create([Category(name="a")])
        objs = list(Category.objects.all())
        for obj in objs:
            obj.name = "b"
        Category.objects.bulk_update(objs, ["name"])
        Category.objects.all().update(name="c")
    finally:
        pre_save.disconnect(handler)
        post_save.disconnect(handler)

    assert fired == [], "Django started emitting bulk signals!"
