from django.core.exceptions import ValidationError
from django.db import models
import uuid


class ProductVariantOptionValue(models.Model):
    """
    Connects a ProductVariant to a ProductOptionValue.

    A variant can contain only one value from each
    ProductOption.

    Ordering is intentionally NOT defined in Meta because
    the natural ordering uses FK traversal
    (option_value__option__sort_order), which would force a
    join on every read. Callers that need ordering must
    apply it explicitly.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # ==================================================
    # Variant
    # ==================================================

    variant = models.ForeignKey(
        "vendors.ProductVariant",
        on_delete=models.CASCADE,
        related_name="variant_option_values",
    )

    # ==================================================
    # Option Value
    # ==================================================

    option_value = models.ForeignKey(
        "vendors.ProductOptionValue",
        on_delete=models.PROTECT,
        related_name="variant_links",
    )

    # ==================================================
    # Timestamp
    # ==================================================

    created_at = models.DateTimeField(auto_now_add=True)

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        # No Meta.ordering by design — see class docstring.

        constraints = [
            models.UniqueConstraint(
                fields=["variant", "option_value"],
                name="unique_variant_option_value",
            ),
        ]

        indexes = [
            models.Index(fields=["variant"]),
            models.Index(fields=["option_value"]),
        ]

    # ==================================================
    # String Representation
    # ==================================================

    def __str__(self):
        return (
            f"{self.variant} - "
            f"{self.option_value.option.name}: "
            f"{self.option_value.name}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):
        """
        Validate the relationship between:

            ProductVariant
                ↓
            Product
                ↓
            ProductOption
                ↓
            ProductOptionValue
        """

        if not self.variant_id:
            raise ValidationError(
                {"variant": "A variant option value must belong to a variant."}
            )

        if not self.option_value_id:
            raise ValidationError(
                {
                    "option_value": (
                        "A variant option value must reference "
                        "an option value."
                    )
                }
            )

        variant_product_id = self.variant.product_id
        option = self.option_value.option
        option_product_id = option.product_id

        if variant_product_id != option_product_id:
            raise ValidationError(
                {
                    "option_value": (
                        "The selected option value does not "
                        "belong to the variant's product."
                    )
                }
            )

        existing = (
            ProductVariantOptionValue.objects
            .filter(
                variant_id=self.variant_id,
                option_value__option_id=option.id,
            )
        )

        if self.pk:
            existing = existing.exclude(pk=self.pk)

        if existing.exists():
            raise ValidationError(
                {
                    "option_value": (
                        "A variant can only have one value "
                        "for each product option."
                    )
                }
            )

    # ==================================================
    # Save
    # ==================================================

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ==================================================
    # Convenience Properties
    # ==================================================

    @property
    def option(self):
        if not self.option_value_id:
            return None
        return self.option_value.option

    @property
    def product(self):
        if not self.variant_id:
            return None
        return self.variant.product

    @property
    def value(self):
        return self.option_value

    @property
    def option_name(self):
        option = self.option
        if option is None:
            return None
        return option.name

    @property
    def value_name(self):
        if not self.option_value_id:
            return None
        return self.option_value.name

    @property
    def display_name(self):
        option_name = self.option_name
        value_name = self.value_name

        if not option_name:
            return value_name
        if not value_name:
            return option_name

        return f"{option_name}: {value_name}"

    @property
    def option_id(self):
        if not self.option_value_id:
            return None
        return self.option_value.option_id