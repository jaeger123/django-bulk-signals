# django-bulk-signals

**Custom signal support for Django bulk operations — with granular field-level diffing.**

This library extends Django's signal framework to support `bulk_create`, `bulk_update`, and queryset `update()` operations. It also helps detect exactly **which fields changed** in each object.

---

## ✨ Features

- `pre_bulk_create`, `post_bulk_create` signals
- `pre_bulk_update`, `post_bulk_update` signals
- `pre_update` for regular `.update()` calls
- Field-level change tracking during bulk operations
- Decorators for easy multi-signal binding
- Drop-in replacement for your model `Manager` or `QuerySet`

---

## 🚀 Installation

```bash
pip install django-advanced-bulk-signals
```

> **Note:** the PyPI name is `django-advanced-bulk-signals`. The name
> `django-bulk-signals` on PyPI is an unrelated project by a different
> author. The import path is still `django_bulk_signals`.

> **Django 3.x only.** Version 0.1.1 is capped at `Django<4.0`; see
> [CHANGELOG.md](CHANGELOG.md).

## 🧠 Usage

1. Use the custom manager:
```python
from django_bulk_signals.managers import CustomManager
from django.db import models


class Customer(models.Model):
    ...
    objects = CustomManager()
```
2. Connect to signals:
```python
from django.dispatch import receiver
from django_bulk_signals.signals import pre_bulk_update


@receiver(pre_bulk_update, sender=Customer)
def customer_bulk_update_handler(sender, **kwargs):
    forward_data = kwargs.get("forward_data")
    print("Changed fields:", forward_data)
```
### Signal Reference
| Signal             | Description            |
| ------------------ | ---------------------- |
| `pre_update`       | Before `.update()`     |
| `pre_bulk_update`  | Before `bulk_update()` |
| `post_bulk_update` | After `bulk_update()`  |
| `pre_bulk_create`  | Before `bulk_create()` |
| `post_bulk_create` | After `bulk_create()`  |

🛠️ Tools
Decorator
```python
from django_bulk_signals.decorators import apply_signals


@apply_signals(Customer, pre_bulk_update, pre_update)
def handler(sender, **kwargs): ...
```
