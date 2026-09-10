"""Field-level diffing helpers used to build signal payloads."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from django.db import models

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["find_specific_updated_values", "find_updated_values"]


def find_specific_updated_values(
    model_instance: models.Model,
    update_kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Return the subset of ``update_kwargs`` that differs from the instance.

    Args:
        model_instance: The instance to compare against, as currently loaded.
        update_kwargs: The keyword arguments passed to ``QuerySet.update()``.

    Returns:
        A mapping of field name to new value, containing only fields whose
        value actually changes.

    .. warning::
       KNOWN BUG #4: ``django_fields`` is keyed by ``field.name``, so a foreign
       key attname such as ``category_id`` is absent and this raises
       ``KeyError``.

       KNOWN BUG #5: the ``except`` branch calls ``ValidationError(detail=...)``,
       which is Django REST Framework's signature, not Django's. Django's
       ``ValidationError`` takes ``(message, code, params)``, so this raises
       ``TypeError`` instead of the intended validation error.

    """
    # Get the Django field objects for the specified fields
    django_fields = {
        field.name: field
        for field in model_instance._meta.fields
        if field.name in update_kwargs
    }

    # Get the current values of the specified fields from the model instance.
    model_values = {field: getattr(model_instance, field) for field in update_kwargs}

    updated_values: dict[str, Any] = {}

    for field_name, new_value in update_kwargs.items():
        model_val = model_values[field_name]
        django_field = django_fields[field_name]

        try:
            converted = django_field.to_python(new_value)
        except ValidationError as ve:
            raise ValidationError(
                detail=f"Error while converting {new_value} to {django_field}, {ve}",
                code="405",
            ) from ve

        # only add to updated_values if the values differ
        if model_val != converted:
            updated_values[field_name] = converted

    return updated_values


def find_updated_values(
    model_instance: models.Model,
    db_instance: models.Model,
    fields: Sequence[str] | None = None,
    updated_foreign_keys: bool = False,
) -> dict[str, Any]:
    """Return the fields of ``model_instance`` that differ from ``db_instance``.

    Args:
        model_instance: The in-memory instance holding the new values.
        db_instance: The instance as currently stored in the database.
        fields: Field names to compare. When omitted, every non-primary-key,
            non-timestamp field is compared.
        updated_foreign_keys: Whether foreign keys are included when ``fields``
            is not given.

    Returns:
        A mapping of field name to new value, containing only changed fields.

    .. warning::
       KNOWN BUG #5 applies here too: the ``except`` branch uses DRF's
       ``ValidationError`` signature and therefore raises ``TypeError``.

    """
    # If fields are not passed in, use the non-primary key field names.
    if not fields:
        base_model_fields = ["created_at", "updated_at"]

        fields = [
            f.name
            for f in model_instance._meta.fields
            if not f.primary_key
            and (updated_foreign_keys or not isinstance(f, models.ForeignKey))
            and f.name not in base_model_fields
        ]

    django_fields = {
        field.name: field
        for field in model_instance._meta.fields
        if field.name in fields
    }

    db_values = {field: getattr(db_instance, field) for field in fields}
    model_values = {field: getattr(model_instance, field) for field in fields}

    updated_values: dict[str, Any] = {}
    for field_name in fields:
        db_val = db_values[field_name]
        model_val = model_values[field_name]
        django_field = django_fields[field_name]

        try:
            converted = django_field.to_python(model_val)
        except ValidationError as ve:
            raise ValidationError(
                detail=(
                    f"Signal Error while converting {model_val} to {django_field}, {ve}"
                ),
                code="405",
            ) from ve

        # only add to updated_values if the values differ
        if converted != db_val:
            updated_values[field_name] = converted

    return updated_values
