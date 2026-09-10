"""Manager and QuerySet that emit signals around Django's bulk operations.

Attach them to a model with either::

    objects = CustomManager()
    # or, to keep other queryset methods chainable:
    objects = CustomManager.from_queryset(MyModelQuerySet)()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models
from django.db.models.expressions import Expression

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

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

__all__ = ["CustomManager", "MyModelQuerySet"]


class CustomManager(models.Manager):
    """Manager whose queryset emits the bulk signals."""

    def get_queryset(self) -> MyModelQuerySet:
        """Return a :class:`MyModelQuerySet` so its overrides are used."""
        return MyModelQuerySet(self.model, using=self._db)


class MyModelQuerySet(models.QuerySet):
    """QuerySet that sends signals around ``update``/``bulk_update``/``bulk_create``."""

    def update(self, **kwargs: object) -> int:
        """Send :data:`~django_bulk_signals.signals.pre_update`, then update.

        The signal carries ``forward_data`` describing which fields actually
        change on which instances. It is skipped entirely when every value is a
        database :class:`~django.db.models.expressions.Expression`, since the
        new values cannot be known before the query runs.

        .. warning::
           KNOWN BUG #6: a bare ``F()`` is a ``Combinable``, not an
           ``Expression``, so it is not caught by the guard below.

           KNOWN BUG #9: ``self.exists()`` costs an extra query, and iterating
           ``self`` materialises every matching row as a model instance, which
           defeats the purpose of a bulk ``UPDATE``.
        """
        if (
            any(not isinstance(value, Expression) for value in kwargs.values())
            and self.exists()
        ):
            forward_data: dict[str, Any] = {"action": "update", "objects": []}
            for obj in self:
                updated_values = find_specific_updated_values(obj, update_kwargs=kwargs)
                if updated_values:  # only add the object if 'fields' is not empty
                    forward_data["objects"].append(
                        {"object": obj, "fields": updated_values}
                    )
            if forward_data.get("objects"):
                pre_update.send(
                    sender=self.model,
                    update_kwargs=kwargs,
                    forward_data=forward_data,
                )

        # The queryset is altered by the update, so there is no reason to send
        # it along afterwards.
        return super().update(**kwargs)

    def bulk_update(
        self,
        objs: Iterable[models.Model],
        fields: Sequence[str],
        batch_size: int | None = None,
    ) -> int:
        """Send the bulk-update signals around ``QuerySet.bulk_update``.

        .. warning::
           KNOWN BUG #2: ``objs`` is iterated here and then handed to
           ``super()``. A generator is therefore exhausted before the real
           update runs, making the call a silent no-op.

           KNOWN BUG #7: the database is queried once per object.

           KNOWN BUG #8: that lookup goes through the *default* manager and
           ignores ``self.db``, so a filtered manager raises ``DoesNotExist``
           and a multi-database setup reads the wrong database.
        """
        forward_data: dict[str, Any] = {"action": "update", "objects": []}
        for obj in objs:
            # obj.pk rather than obj.id, as 'id' is not the pk in every table.
            updated_values = find_updated_values(
                obj, obj.__class__.objects.get(pk=obj.pk), fields=fields
            )
            if updated_values:  # only add the object if 'fields' is not empty
                forward_data["objects"].append(
                    {"object": obj, "fields": updated_values}
                )

        update_kwargs = {"objs": objs, "fields": fields, "batch_size": batch_size}
        if fd_exist := forward_data.get("objects"):
            pre_bulk_update.send(
                sender=self.model,
                update_kwargs=update_kwargs,
                forward_data=forward_data,
            )

        res = super().bulk_update(objs, fields, batch_size)

        if fd_exist:
            post_bulk_update.send(
                sender=self.model,
                update_kwargs=update_kwargs,
                forward_data=forward_data,
            )
        return res

    def bulk_create(
        self,
        objs: Iterable[models.Model],
        batch_size: int | None = None,
        ignore_conflicts: bool = False,
    ) -> list[models.Model]:
        """Send the bulk-create signals around ``QuerySet.bulk_create``.

        .. warning::
           KNOWN BUG #3: this signature is frozen at Django 4.0's. Django 4.1
           added ``update_conflicts``, ``update_fields`` and ``unique_fields``,
           which therefore raise ``TypeError`` here - and that also makes
           ``abulk_create()`` unusable, since it forwards them unconditionally.
           The fix is a ``**kwargs`` passthrough.

           KNOWN BUG #2: ``objs`` is iterated before being handed to
           ``super()``, so a generator is silently dropped.
        """
        forward_data: dict[str, Any] = {
            "action": "save",
            "objects": [{"object": obj} for obj in objs],
        }
        pre_bulk_create.send(
            sender=self.model,
            objs=objs,
            batch_size=batch_size,
            forward_data=forward_data,
        )
        res = super().bulk_create(objs, batch_size, ignore_conflicts)
        post_bulk_create.send(
            sender=self.model,
            objs=objs,
            batch_size=batch_size,
            forward_data=forward_data,
        )
        return res
