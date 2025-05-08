from django.core.exceptions import ValidationError
from django.db import models


def find_specific_updated_values(model_instance, update_kwargs):

    # Get the Django field objects for the specified fields
    django_fields = {
        field.name: field
        for field in model_instance._meta.fields
        if field.name in update_kwargs
    }

    # Get the current values of the specified fields from the model instance.
    model_values = {field: getattr(model_instance, field) for field in update_kwargs}

    # Prepare the dictionary to hold the updated values
    updated_values = {}

    for field_name, new_value in update_kwargs.items():
        model_val = model_values[field_name]
        django_field = django_fields[field_name]

        try:
            new_value = django_field.to_python(new_value)
        except ValidationError as ve:
            raise ValidationError(
                detail=f"Error while converting {new_value} to {django_field}, {str(ve)}",
                code="405",
            )

        # Compare the new value with the current value
        if model_val != new_value:
            updated_values[
                field_name
            ] = new_value  # only add to updated_values if values are different

    return updated_values


def find_updated_values(
    model_instance, db_instance, fields=None, updated_foreign_keys=False
):

    # If fields are not passed in, get the non-primary key field names of the model instance.
    if not fields:
        base_model_fields = ["created_at", "updated_at"]

        fields = [
            f.name
            for f in model_instance._meta.fields
            if not f.primary_key
            and (updated_foreign_keys or not isinstance(f, models.ForeignKey))
            and f.name not in base_model_fields
        ]

    # Get the Django field objects for the specified fields
    django_fields = {
        field.name: field
        for field in model_instance._meta.fields
        if field.name in fields
    }

    # Get the values of the fields from the database instance.
    db_values = {field: getattr(db_instance, field) for field in fields}

    # Get the values of the fields from the model instance.
    model_values = {field: getattr(model_instance, field) for field in fields}

    # Find the differences between the two sets of values.
    updated_values = {}
    for field_name in fields:
        db_val = db_values[field_name]
        model_val = model_values[field_name]
        django_field = django_fields[field_name]

        try:
            model_val = django_field.to_python(model_val)
        except ValidationError as ve:
            raise ValidationError(
                detail=f"Signal Error while converting {model_val} to {django_field}, {str(ve)}",
                code="405",
            )

        if model_val != db_val:
            updated_values[
                field_name
            ] = model_val  # only add to updated_values if values are different

    return updated_values
