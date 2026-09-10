"""Behavioural tests for django_bulk_signals.

Tests marked with :func:`known_bug` are strict xfails documenting a real defect
found in the 2026-09-10 audit. Because ``strict=True``, an unexpected pass
fails the build - so fixing a bug forces its marker to be removed, and the bug
list cannot drift out of sync with the code.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import django
import pytest
from django.core.exceptions import ValidationError
from django.db.models import F, Value

from tests.models import (
    IMPORT_ERROR,
    Category,
    Customer,
    FilteredCustomer,
    UniqueCustomer,
)

if TYPE_CHECKING:
    from types import ModuleType

    from tests.conftest import Recorder

DJ = django.VERSION[:2]

pytestmark = [
    pytest.mark.skipif(
        IMPORT_ERROR is not None,
        reason=f"KNOWN BUG #1 - package does not import on Django "
        f"{django.get_version()}: {IMPORT_ERROR}",
    ),
    pytest.mark.django_db,
]


def known_bug(number: int, reason: str) -> pytest.MarkDecorator:
    """Mark a test as a strict xfail documenting a known, unfixed defect."""
    return pytest.mark.xfail(reason=f"KNOWN BUG #{number}: {reason}", strict=True)


@pytest.fixture
def customers() -> list[Customer]:
    """Two saved customers."""
    return [
        Customer.objects.create(name="one", count=1),
        Customer.objects.create(name="two", count=2),
    ]


# --------------------------------------------------------------- bulk_create


def test_pre_and_post_bulk_create_fire(record: Any, signals: ModuleType) -> None:
    pre: Recorder = record(signals.pre_bulk_create, Customer)
    post: Recorder = record(signals.post_bulk_create, Customer)

    Customer.objects.bulk_create([Customer(name="a"), Customer(name="b")])

    assert pre.count == 1
    assert post.count == 1
    assert len(pre.calls[0]["forward_data"]["objects"]) == 2


def test_bulk_create_actually_inserts() -> None:
    Customer.objects.bulk_create([Customer(name="a"), Customer(name="b")])
    assert Customer.objects.count() == 2


@known_bug(
    2,
    "objs is iterated to build forward_data, then the exhausted iterator is "
    "handed to super() - nothing is inserted, silently.",
)
def test_bulk_create_with_generator() -> None:
    Customer.objects.bulk_create(Customer(name=f"gen{i}") for i in range(3))
    assert Customer.objects.count() == 3


def test_bulk_create_ignore_conflicts() -> None:
    UniqueCustomer.objects.create(code="x", name="orig")
    UniqueCustomer.objects.bulk_create(
        [UniqueCustomer(code="x", name="dupe")], ignore_conflicts=True
    )
    assert UniqueCustomer.objects.count() == 1


@pytest.mark.skipif(DJ < (4, 1), reason="update_conflicts added in Django 4.1")
@known_bug(
    3,
    "bulk_create() re-declares Django 4.0's signature, so the update_conflicts/"
    "update_fields/unique_fields added in 4.1 raise TypeError. "
    "Fix: **kwargs passthrough.",
)
def test_bulk_create_update_conflicts() -> None:
    UniqueCustomer.objects.create(code="x", name="orig")
    UniqueCustomer.objects.bulk_create(
        [UniqueCustomer(code="x", name="updated")],
        update_conflicts=True,
        update_fields=["name"],
        unique_fields=["code"],
    )
    assert UniqueCustomer.objects.get(code="x").name == "updated"


def test_bulk_create_empty_list(record: Any, signals: ModuleType) -> None:
    pre: Recorder = record(signals.pre_bulk_create, Customer)
    Customer.objects.bulk_create([])
    assert pre.count == 1


def test_bulk_create_batch_size_kwarg() -> None:
    Customer.objects.bulk_create(
        [Customer(name=f"n{i}") for i in range(5)], batch_size=2
    )
    assert Customer.objects.count() == 5


def test_bulk_create_via_related_manager(record: Any, signals: ModuleType) -> None:
    category = Category.objects.create(name="c")
    pre: Recorder = record(signals.pre_bulk_create, Customer)

    category.customers.bulk_create([Customer(name="rel")])

    assert Customer.objects.count() == 1
    assert pre.count == 1


# --------------------------------------------------------------- bulk_update


def test_pre_and_post_bulk_update_fire(
    customers: list[Customer], record: Any, signals: ModuleType
) -> None:
    first = customers[0]
    first.name = "one-changed"
    pre: Recorder = record(signals.pre_bulk_update, Customer)
    post: Recorder = record(signals.post_bulk_update, Customer)

    Customer.objects.bulk_update([first], ["name"])

    assert pre.count == 1
    assert post.count == 1


def test_bulk_update_reports_only_changed_fields(
    customers: list[Customer], record: Any, signals: ModuleType
) -> None:
    first, second = customers
    first.name = "changed"
    second.name = "two"  # unchanged
    pre: Recorder = record(signals.pre_bulk_update, Customer)

    Customer.objects.bulk_update([first, second], ["name"])

    assert pre.changed_fields() == {first.pk: {"name": "changed"}}


def test_bulk_update_no_change_sends_nothing(
    customers: list[Customer], record: Any, signals: ModuleType
) -> None:
    pre: Recorder = record(signals.pre_bulk_update, Customer)
    Customer.objects.bulk_update([customers[0]], ["name"])
    assert pre.count == 0


def test_bulk_update_persists(customers: list[Customer]) -> None:
    first = customers[0]
    first.name = "persisted"
    Customer.objects.bulk_update([first], ["name"])
    first.refresh_from_db()
    assert first.name == "persisted"


@pytest.mark.skipif(DJ < (4, 0), reason="return value added in Django 4.0")
def test_bulk_update_return_value(customers: list[Customer]) -> None:
    first = customers[0]
    first.name = "rv"
    assert Customer.objects.bulk_update([first], ["name"]) == 1


@known_bug(2, "same double-iteration defect as bulk_create - a silent no-op.")
def test_bulk_update_with_generator(customers: list[Customer]) -> None:
    first = customers[0]
    first.name = "gen"
    Customer.objects.bulk_update((o for o in [first]), ["name"])
    first.refresh_from_db()
    assert first.name == "gen"


@known_bug(
    7,
    "obj.__class__.objects.get(pk=obj.pk) runs once per object, so "
    "bulk_update() is O(n) queries. Fix: a single bulk fetch.",
)
def test_bulk_update_query_count(django_assert_max_num_queries: Any) -> None:
    Customer.objects.bulk_create([Customer(name=f"p{i}") for i in range(25)])
    objs = list(Customer.objects.all())
    for i, obj in enumerate(objs):
        obj.name = f"q{i}"

    with django_assert_max_num_queries(5):
        Customer.objects.bulk_update(objs, ["name"])


def test_bulk_update_batch_size_keyword(customers: list[Customer]) -> None:
    first = customers[0]
    first.name = "bs"
    Customer.objects.bulk_update([first], ["name"], batch_size=1)
    first.refresh_from_db()
    assert first.name == "bs"


@known_bug(
    8,
    "the per-object lookup uses the *default* manager and ignores self.db, so "
    "a filtered (soft-delete) manager raises DoesNotExist and multi-db reads "
    "the wrong database. Fix: _base_manager.using(self.db).",
)
def test_bulk_update_on_filtered_default_manager() -> None:
    hidden = FilteredCustomer.objects.create(name="f", is_active=True)
    FilteredCustomer.objects.filter(pk=hidden.pk).update(is_active=False)
    hidden.name, hidden.is_active = "renamed", False

    FilteredCustomer.objects.bulk_update([hidden], ["name"])

    assert FilteredCustomer._base_manager.get(pk=hidden.pk).name == "renamed"


# ------------------------------------------------------------ QuerySet.update


@pytest.fixture
def customer() -> Customer:
    """One saved customer."""
    return Customer.objects.create(name="one", count=1)


def test_pre_update_fires(customer: Customer, record: Any, signals: ModuleType) -> None:
    pre: Recorder = record(signals.pre_update, Customer)
    Customer.objects.filter(pk=customer.pk).update(name="new")
    assert pre.count == 1


def test_update_reports_changed_fields(
    customer: Customer, record: Any, signals: ModuleType
) -> None:
    pre: Recorder = record(signals.pre_update, Customer)
    Customer.objects.filter(pk=customer.pk).update(name="new")
    assert pre.changed_fields() == {customer.pk: {"name": "new"}}


def test_update_no_change_sends_nothing(
    customer: Customer, record: Any, signals: ModuleType
) -> None:
    pre: Recorder = record(signals.pre_update, Customer)
    Customer.objects.filter(pk=customer.pk).update(name="one")
    assert pre.count == 0


def test_update_persists_and_returns_rowcount(customer: Customer) -> None:
    assert Customer.objects.filter(pk=customer.pk).update(name="new") == 1
    customer.refresh_from_db()
    assert customer.name == "new"


@known_bug(
    4,
    "find_specific_updated_values indexes _meta.fields by .name, but "
    "update(category_id=...) uses the FK attname - KeyError. This is the most "
    "idiomatic Django update there is.",
)
def test_update_with_fk_id_attname(customer: Customer) -> None:
    category = Category.objects.create(name="cat")
    Customer.objects.filter(pk=customer.pk).update(category_id=category.pk)
    customer.refresh_from_db()
    assert customer.category_id == category.pk


@known_bug(
    5,
    "to_python() on a model instance raises ValidationError, and the handler "
    "then calls ValidationError(detail=...) - DRF's signature - so it dies "
    "with TypeError instead.",
)
def test_update_with_fk_object(customer: Customer) -> None:
    category = Category.objects.create(name="cat")
    Customer.objects.filter(pk=customer.pk).update(category=category)
    customer.refresh_from_db()
    assert customer.category_id == category.pk


@known_bug(
    6,
    "F() subclasses Combinable, not Expression, so a bare F() slips past the "
    "isinstance guard into to_python(). F('x') + 1 works because "
    "CombinedExpression *is* an Expression.",
)
def test_update_with_bare_f_expression(customer: Customer) -> None:
    Customer.objects.filter(pk=customer.pk).update(count=F("id"))
    customer.refresh_from_db()
    assert customer.count == customer.pk


def test_update_with_combined_f_expression(customer: Customer) -> None:
    Customer.objects.filter(pk=customer.pk).update(count=F("count") + 1)
    customer.refresh_from_db()
    assert customer.count == 2


def test_update_with_value_expression(customer: Customer) -> None:
    Customer.objects.filter(pk=customer.pk).update(name=Value("v"))
    customer.refresh_from_db()
    assert customer.name == "v"


def test_update_empty_queryset(record: Any, signals: ModuleType) -> None:
    pre: Recorder = record(signals.pre_update, Customer)
    assert Customer.objects.filter(name="nope").update(name="x") == 0
    assert pre.count == 0


def test_update_on_deferred_queryset(customer: Customer) -> None:
    Customer.objects.only("id").filter(pk=customer.pk).update(name="deferred")
    customer.refresh_from_db()
    assert customer.name == "deferred"


@known_bug(
    9,
    "update() calls .exists() and then iterates the whole queryset, "
    "materialising every matching row as a model instance - defeating the "
    "point of a bulk UPDATE.",
)
def test_update_does_not_materialise_the_queryset() -> None:
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    Customer.objects.bulk_create([Customer(name=f"b{i}") for i in range(10)])
    with CaptureQueriesContext(connection) as ctx:
        Customer.objects.all().update(email="x@y.z")

    selects = [
        q
        for q in ctx.captured_queries
        if q["sql"].lstrip().upper().startswith("SELECT") and "LIMIT 1" not in q["sql"]
    ]
    assert selects == []


@known_bug(
    5,
    "ValidationError(detail=..., code=...) is DRF's signature; Django's takes "
    "(message, code, params). Every error path raises TypeError instead.",
)
def test_update_invalid_value_raises_clean_error(customer: Customer) -> None:
    with pytest.raises(ValidationError):
        Customer.objects.filter(pk=customer.pk).update(count="not-an-int")


def test_update_decimal_field(
    customer: Customer, record: Any, signals: ModuleType
) -> None:
    pre: Recorder = record(signals.pre_update, Customer)
    Customer.objects.filter(pk=customer.pk).update(balance=Decimal("5.00"))
    assert pre.changed_fields() == {customer.pk: {"balance": Decimal("5.00")}}


# ----------------------------------------------------------------- decorator


def test_apply_signals_binds_handler(signals: ModuleType) -> None:
    from django_bulk_signals.decorators import apply_signals

    seen: list[dict[str, Any]] = []

    @apply_signals(Customer, signals.pre_bulk_create, signals.post_bulk_create)
    def handler(sender: type, **kwargs: object) -> None:  # noqa: ARG001
        seen.append(kwargs)

    Customer.objects.bulk_create([Customer(name="d")])
    assert len(seen) == 2


# --------------------------------------------------------------------- async


@pytest.mark.skipif(DJ < (4, 1), reason="async QuerySet interface added in Django 4.1")
def test_aupdate_triggers_signal(record: Any, signals: ModuleType) -> None:
    """Django's a* methods delegate to the sync ones, so signals survive."""
    from asgiref.sync import async_to_sync

    customer = Customer.objects.create(name="a")
    pre: Recorder = record(signals.pre_update, Customer)

    async_to_sync(Customer.objects.filter(pk=customer.pk).aupdate)(name="b")

    customer.refresh_from_db()
    assert customer.name == "b"
    assert pre.count == 1


@pytest.mark.skipif(DJ < (4, 1), reason="abulk_create added in Django 4.1")
@known_bug(
    3,
    "abulk_create() forwards update_conflicts/update_fields/unique_fields "
    "unconditionally, so the frozen bulk_create() signature makes the entire "
    "async path unusable.",
)
def test_abulk_create_triggers_signal(record: Any, signals: ModuleType) -> None:
    from asgiref.sync import async_to_sync

    pre: Recorder = record(signals.pre_bulk_create, Customer)
    async_to_sync(Customer.objects.abulk_create)([Customer(name="a")])

    assert Customer.objects.count() == 1
    assert pre.count == 1


@pytest.mark.skipif(DJ < (4, 1), reason="abulk_update added in Django 4.1")
def test_abulk_update_triggers_signal(record: Any, signals: ModuleType) -> None:
    from asgiref.sync import async_to_sync

    customer = Customer.objects.create(name="a")
    customer.name = "b"
    pre: Recorder = record(signals.pre_bulk_update, Customer)

    async_to_sync(Customer.objects.abulk_update)([customer], ["name"])

    customer.refresh_from_db()
    assert customer.name == "b"
    assert pre.count == 1
