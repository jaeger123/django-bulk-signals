from django.db import models
from django.db.models.expressions import Expression

from django_bulk_signals.signals import pre_update, pre_bulk_update, post_bulk_update, pre_bulk_create, post_bulk_create
from django_bulk_signals.utils import find_specific_updated_values, find_updated_values


class CustomManager(models.Manager):
    def get_queryset(self):
        # this is to use your custom queryset methods
        return MyModelQuerySet(self.model, using=self._db)


class MyModelQuerySet(models.QuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update(self, **kwargs):
        if any(not isinstance(value, Expression) for value in kwargs.values()):
            if self.exists():
                forward_data = {"action": "update", "objects": []}
                for obj in self:
                    updated_values = find_specific_updated_values(
                        obj, update_kwargs=kwargs
                    )
                    if updated_values:  # only add the object if 'fields' is not empty
                        forward_data["objects"].append(
                            {
                                "object": obj,
                                "fields": updated_values,
                            }
                        )
                if forward_data.get("objects"):
                    pre_update.send(
                        sender=self.model,
                        update_kwargs=kwargs,
                        forward_data=forward_data,
                    )
                    # update_history(objs=self)
        res = super(MyModelQuerySet, self).update(**kwargs)

        # The queryset will be altered after the update call
        # so no reason to send it.
        return res

    def bulk_update(self, objs, fields, batch_size=None):
        forward_data = {"action": "update", "objects": []}
        for obj in objs:
            # obj.pk as id not in all tables.
            updated_values = find_updated_values(
                obj, obj.__class__.objects.get(pk=obj.pk), fields=fields
            )
            if updated_values:  # only add the object if 'fields' is not empty
                forward_data["objects"].append(
                    {
                        "object": obj,
                        "fields": updated_values,
                    }
                )
        if fd_exist := forward_data.get("objects"):
            pre_bulk_update.send(
                sender=self.model,
                update_kwargs={
                    "objs": objs,
                    "fields": fields,
                    "batch_size": batch_size,
                },
                forward_data=forward_data,
            )
        res = super().bulk_update(objs, fields, batch_size)
        if fd_exist:
            post_bulk_update.send(
                sender=self.model,
                update_kwargs={
                    "objs": objs,
                    "fields": fields,
                    "batch_size": batch_size,
                },
                forward_data=forward_data,
            )
        return res

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False):
        forward_data = {"action": "save", "objects": []}
        for obj in objs:
            forward_data["objects"].append({"object": obj})
        pre_bulk_create.send(
            sender=self.model,
            objs=objs,
            batch_size=batch_size,
            forward_data=forward_data,
        )
        res = super(MyModelQuerySet, self).bulk_create(
            objs, batch_size, ignore_conflicts
        )
        post_bulk_create.send(
            sender=self.model,
            objs=objs,
            batch_size=batch_size,
            forward_data=forward_data,
        )
        return res


# in model add :
# objects = CustomManager.from_queryset(MyModelQuerySet)()