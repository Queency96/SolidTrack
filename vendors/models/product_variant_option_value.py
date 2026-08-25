from django.core.exceptions import ValidationError
from django.db import models


class ProductVariantOptionValue(models.Model):
    """
    Connects a ProductVariant to a ProductOptionValue.

    Example:

        Product:
            T-Shirt

        Variant:
            Black / Medium

        Relationships:

            Variant
                │
                ├── Color → Black
                └── Size  → Medium

    A variant can contain only one value from each
    ProductOption.

    Therefore this is valid:

        Color → Black
        Size  → Medium

    But this is invalid:

        Color → Black
        Color → Blue
    """

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

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        ordering = [
            "option_value__option__sort_order",
            "option_value__sort_order",
            "option_value__name",
        ]

        constraints = [

            # ------------------------------------------
            # Same option value cannot be assigned
            # to the same variant twice.
            # ------------------------------------------

            models.UniqueConstraint(
                fields=[
                    "variant",
                    "option_value",
                ],
                name=(
                    "unique_variant_option_value"
                ),
            ),

        ]

        indexes = [

            models.Index(
                fields=[
                    "variant",
                ],
            ),

            models.Index(
                fields=[
                    "option_value",
                ],
            ),

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

        # ----------------------------------------------
        # Variant
        # ----------------------------------------------

        if not self.variant_id:

            raise ValidationError(
                {
                    "variant": (
                        "A variant option value "
                        "must belong to a variant."
                    )
                }
            )

        # ----------------------------------------------
        # Option Value
        # ----------------------------------------------

        if not self.option_value_id:

            raise ValidationError(
                {
                    "option_value": (
                        "A variant option value "
                        "must reference an option "
                        "value."
                    )
                }
            )

        # ----------------------------------------------
        # Resolve relationships
        # ----------------------------------------------

        variant_product_id = (
            self.variant.product_id
        )

        option = self.option_value.option

        option_product_id = (
            option.product_id
        )

        # ----------------------------------------------
        # Product ownership
        # ----------------------------------------------

        if (
            variant_product_id
            != option_product_id
        ):

            raise ValidationError(
                {
                    "option_value": (
                        "The selected option value "
                        "does not belong to the "
                        "variant's product."
                    )
                }
            )

        # ----------------------------------------------
        # One value per option
        # ----------------------------------------------
        #
        # Database-level UniqueConstraint cannot
        # directly enforce this because option_id
        # belongs to ProductOption, not this model.
        #
        # Therefore we validate it here.
        # ----------------------------------------------

        existing = (
            ProductVariantOptionValue.objects
            .filter(
                variant_id=self.variant_id,
                option_value__option_id=option.id,
            )
        )

        if self.pk:

            existing = existing.exclude(
                pk=self.pk,
            )

        if existing.exists():

            raise ValidationError(
                {
                    "option_value": (
                        "A variant can only have "
                        "one value for each "
                        "product option."
                    )
                }
            )

    # ==================================================
    # Save
    # ==================================================

    def save(
        self,
        *args,
        **kwargs,
    ):

        self.full_clean()

        super().save(
            *args,
            **kwargs,
        )

    # ==================================================
    # Convenience Properties
    # ==================================================

    @property
    def option(self):
        """
        Return the ProductOption associated with
        this selected value.
        """

        if not self.option_value_id:
            return None

        return self.option_value.option

    @property
    def product(self):
        """
        Return the product associated with this
        variant-option relationship.
        """

        if not self.variant_id:
            return None

        return self.variant.product

    @property
    def value(self):
        """
        Return the selected ProductOptionValue.
        """

        return self.option_value

    @property
    def option_name(self):
        """
        Return the option name.

        Example:

            Color
        """

        option = self.option

        if option is None:
            return None

        return option.name

    @property
    def value_name(self):
        """
        Return the selected value name.

        Example:

            Black
        """

        if not self.option_value_id:
            return None

        return self.option_value.name

    # ==================================================
    # Display
    # ==================================================

    @property
    def display_name(self):
        """
        Return a human-readable option/value pair.

        Example:

            Color: Black
        """

        option_name = self.option_name
        value_name = self.value_name

        if not option_name:
            return value_name

        if not value_name:
            return option_name

        return (
            f"{option_name}: "
            f"{value_name}"
        )
    
    @property
    def option_id(self):
        """
        Return the selected ProductOption ID.
        """

        if not self.option_value_id:
            return None

        return self.option_value.option_id