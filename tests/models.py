"""Models for the test suite.

The package under test currently fails to import on Django >= 4.0, so the
import is guarded: the app still loads (otherwise Django cannot even start and
we would get no test signal at all), and the behavioural tests skip themselves
with the real reason. tests/test_compat.py asserts the import outcome directly.
"""

from django.db import models

try:
    from django_bulk_signals.managers import CustomManager

    IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - depends on Django version
    IMPORT_ERROR = exc
    CustomManager = models.Manager


class Category(models.Model):
    """A trivial related model, used for the foreign-key tests."""

    name = models.CharField(max_length=50)

    def __str__(self) -> str:
        """Return the category name."""
        return self.name


class ActiveOnlyManager(CustomManager):
    """A *filtered* default manager - very common in real projects."""

    def get_queryset(self) -> models.QuerySet:
        """Return only active rows, hiding the rest from the default manager."""
        return super().get_queryset().filter(is_active=True)


class Customer(models.Model):
    """The main fixture model, covering a spread of field types."""

    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, default="")
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="customers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomManager()

    def __str__(self) -> str:
        """Return the customer name."""
        return self.name


class UniqueCustomer(models.Model):
    """Separate model for conflict/upsert tests."""

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    objects = CustomManager()

    def __str__(self) -> str:
        """Return the unique code."""
        return self.code


class FilteredCustomer(models.Model):
    """Model whose *default* manager hides inactive rows."""

    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    objects = ActiveOnlyManager()

    def __str__(self) -> str:
        """Return the customer name."""
        return self.name
