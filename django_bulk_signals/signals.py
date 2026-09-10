"""Signals emitted around Django's bulk queryset operations.

Django does not emit ``pre_save``/``post_save`` for ``bulk_create()``,
``bulk_update()`` or ``QuerySet.update()``, and still does not as of Django 6.1.
These signals fill that gap. They are sent by
:class:`django_bulk_signals.managers.MyModelQuerySet`.

Every signal is sent with ``sender`` set to the model class and a
``forward_data`` keyword argument of the shape::

    {"action": "update" | "save",
     "objects": [{"object": <instance>, "fields": {<name>: <new value>}}]}

.. warning::
   KNOWN BUG #1: the ``providing_args`` argument below was deprecated in Django
   3.0 and **removed in Django 4.0**, so importing this module raises
   ``TypeError`` on Django >= 4.0. It is retained here deliberately so that the
   characterisation tests in ``tests/test_compat.py`` keep describing the
   released 0.1.x behaviour. Removing it is the first step of the 1.0.0 fix.
"""

from django.dispatch import Signal

#: Sent before ``QuerySet.update()``, with ``update_kwargs`` and ``forward_data``.
pre_update = Signal(providing_args=["kwargs"])
#: Sent before ``QuerySet.bulk_update()``, with ``update_kwargs``/``forward_data``.
pre_bulk_update = Signal(providing_args=["queryset", "update_kwargs"])
#: Sent after ``QuerySet.bulk_update()``, with ``update_kwargs``/``forward_data``.
post_bulk_update = Signal(providing_args=["update_kwargs", "queryset"])
#: Sent before ``QuerySet.bulk_create()``, with ``objs``/``batch_size``.
pre_bulk_create = Signal(providing_args=["objs", "batch_size"])
#: Sent after ``QuerySet.bulk_create()``, with ``objs``/``batch_size``.
post_bulk_create = Signal(providing_args=["objs", "batch_size"])

__all__ = [
    "post_bulk_create",
    "post_bulk_update",
    "pre_bulk_create",
    "pre_bulk_update",
    "pre_update",
]
