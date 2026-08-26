from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
import uuid


class ProductOption(models.Model):
    """
    Defines an option/attribute used to create
    product variants.

    Examples:

        Color
        Size
        Storage
        Material
        Flavor

    A ProductOption belongs to exactly one Product.

    Example:

        T-Shirt
            ├── Color
            └── Size
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # ==================================================
    # Product
    # ==================================================

    product = models.ForeignKey(
        "vendors.Product",
        on_delete=models.CASCADE,
        related_name="options",
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
                    "product",
                    "name",
                ],
                name=(
                    "unique_product_option_name"
                ),
            ),

            models.UniqueConstraint(
                fields=[
                    "product",
                    "slug",
                ],
                name=(
                    "unique_product_option_slug"
                ),
            ),

        ]

        indexes = [

            models.Index(
                fields=[
                    "product",
                    "is_active",
                ],
            ),

            models.Index(
                fields=[
                    "product",
                    "sort_order",
                ],
            ),

        ]

    # ==================================================
    # String Representation
    # ==================================================

    def __str__(self):

        return (
            f"{self.product.name} - "
            f"{self.name}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):
        """
        Validate product option configuration.
        """

        if self.product_id is None:

            raise ValidationError(
                {
                    "product": (
                        "A product option must "
                        "belong to a product."
                    )
                }
            )

        # ----------------------------------------------
        # Name
        # ----------------------------------------------

        if not self.name or not self.name.strip():

            raise ValidationError(
                {
                    "name": (
                        "Option name cannot "
                        "be empty."
                    )
                }
            )

        # ----------------------------------------------
        # Slug
        # ----------------------------------------------

        if not self.slug or not self.slug.strip():

            raise ValidationError(
                {
                    "slug": (
                        "Option slug cannot "
                        "be empty."
                    )
                }
            )

        # ----------------------------------------------
        # Normalize comparison
        # ----------------------------------------------

        self.name = self.name.strip()

        self.slug = slugify(
            self.slug,
        )

        if not self.slug:

            raise ValidationError(
                {
                    "slug": (
                        "Option slug must contain "
                        "valid characters."
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
    # Values
    # ==================================================

    @property
    def value_count(self):
        """
        Return the total number of values defined
        for this option.
        """

        return self.values.count()

    # ==================================================
    # Active Values
    # ==================================================

    @property
    def active_value_count(self):
        """
        Return the number of active option values.
        """

        return self.values.filter(
            is_active=True,
        ).count()

    # ==================================================
    # Has Values
    # ==================================================

    @property
    def has_values(self):
        """
        Determine whether this option has values.
        """

        return self.values.exists()

    # ==================================================
    # Has Active Values
    # ==================================================

    @property
    def has_active_values(self):
        """
        Determine whether this option has at least
        one active value.
        """

        return self.values.filter(
            is_active=True,
        ).exists()

    # ==================================================
    # Active Values
    # ==================================================

    @property
    def active_values(self):
        """
        Return active option values.
        """

        return self.values.filter(
            is_active=True,
        )

    # ==================================================
    # Variant Count
    # ==================================================

    @property
    def variant_count(self):
        """
        Return the number of variants using values
        belonging to this option.
        """

        return (
            self.values
            .filter(
                variant_values__isnull=False,
            )
            .values(
                "variant_values__variant",
            )
            .distinct()
            .count()
        )