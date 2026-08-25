from django.core.exceptions import ValidationError
from django.db import models


class ProductOptionValue(models.Model):
    """
    Represents one selectable value belonging to a
    ProductOption.

    Examples:

        Color
            ├── Black
            ├── White
            └── Blue

        Size
            ├── Small
            ├── Medium
            └── Large

        Storage
            ├── 128GB
            ├── 256GB
            └── 512GB
    """

    # ==================================================
    # Option
    # ==================================================

    option = models.ForeignKey(
        "vendors.ProductOption",
        on_delete=models.CASCADE,
        related_name="values",
    )

    # ==================================================
    # Identity
    # ==================================================

    name = models.CharField(
        max_length=100,
    )

    slug = models.SlugField(
        max_length=120,
    )

    # ==================================================
    # Display
    # ==================================================

    sort_order = models.PositiveIntegerField(
        default=0,
    )

    # ==================================================
    # Status
    # ==================================================

    is_active = models.BooleanField(
        default=True,
    )

    # ==================================================
    # Timestamps
    # ==================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        ordering = [
            "sort_order",
            "name",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "option",
                    "name",
                ],
                name=(
                    "unique_option_value_name"
                ),
            ),

            models.UniqueConstraint(
                fields=[
                    "option",
                    "slug",
                ],
                name=(
                    "unique_option_value_slug"
                ),
            ),

        ]

        indexes = [

            models.Index(
                fields=[
                    "option",
                    "is_active",
                ],
            ),

            models.Index(
                fields=[
                    "option",
                    "sort_order",
                ],
            ),

        ]

    # ==================================================
    # String Representation
    # ==================================================

    def __str__(self):

        return (
            f"{self.option.name}: "
            f"{self.name}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):
        """
        Validate option value configuration.
        """

        # ----------------------------------------------
        # Option
        # ----------------------------------------------

        if self.option_id is None:

            raise ValidationError(
                {
                    "option": (
                        "An option value must "
                        "belong to an option."
                    )
                }
            )

        # ----------------------------------------------
        # Name
        # ----------------------------------------------

        if not self.name.strip():

            raise ValidationError(
                {
                    "name": (
                        "Option value name "
                        "cannot be empty."
                    )
                }
            )

        # ----------------------------------------------
        # Slug
        # ----------------------------------------------

        if not self.slug.strip():

            raise ValidationError(
                {
                    "slug": (
                        "Option value slug "
                        "cannot be empty."
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
    # Product
    # ==================================================

    @property
    def product(self):
        """
        Return the product this option value
        ultimately belongs to.
        """

        return self.option.product

    # ==================================================
    # Product ID
    # ==================================================

    @property
    def product_id(self):
        """
        Return the parent product ID.
        """

        return self.option.product_id

    # ==================================================
    # Option
    # ==================================================

    @property
    def option_name(self):
        """
        Return the name of the parent option.
        """

        return self.option.name

    # ==================================================
    # Availability
    # ==================================================

    @property
    def is_available(self):
        """
        Determine whether this option value can
        currently be selected.
        """

        return (
            self.is_active
            and self.option.is_active
            and self.option.product.is_available
        )

    # ==================================================
    # Variant Usage
    # ==================================================

    @property
    def variant_count(self):
        """
        Return the number of variants using this
        option value.
        """

        return self.variant_links.count()

    # ==================================================
    # Active Variant Usage
    # ==================================================

    @property
    def active_variant_count(self):
        """
        Return the number of active variants using
        this option value.
        """

        return self.variant_links.filter(
            variant__is_active=True,
        ).count()