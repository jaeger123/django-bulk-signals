from django.dispatch import Signal

pre_update = Signal(providing_args=["kwargs"])
pre_bulk_update = Signal(providing_args=["queryset", "update_kwargs"])
post_bulk_update = Signal(providing_args=["update_kwargs", "queryset"])
pre_bulk_create = Signal(providing_args=["objs", "batch_size"])
post_bulk_create = Signal(providing_args=["objs", "batch_size"])