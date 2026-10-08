import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


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

    product = models.ForeignKey(
        "vendors.Product",
        on_delete=models.CASCADE,
        related_name="options",
    )

    name = models.CharField(
        max_length=100,
    )

    slug = models.SlugField(
        max_length=120,
    )

    sort_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = [
            "sort_order",
            "name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["product", "name"],
                name="unique_product_option_name",
            ),
            models.UniqueConstraint(
                fields=["product", "slug"],
                name="unique_product_option_slug",
            ),
        ]

        indexes = [
            models.Index(
                fields=["product", "is_active"],
            ),
            models.Index(
                fields=["product", "sort_order"],
            ),
        ]

    def __str__(self):

        return f"{self.product.name} - {self.name}"

    def clean(self):

        if self.product_id is None:

            raise ValidationError(
                {
                    "product": (
                        "A product option must belong "
                        "to a product."
                    )
                }
            )

        # --------------------------------------------------
        # Normalize before validating, so `"   "` does not
        # slip through the empty-name check.
        # --------------------------------------------------

        if self.name:
            self.name = self.name.strip()

        if not self.name:

            raise ValidationError(
                {
                    "name": (
                        "Option name cannot be empty."
                    )
                }
            )

        if self.slug:
            self.slug = slugify(self.slug)

        if not self.slug:

            raise ValidationError(
                {
                    "slug": (
                        "Option slug must contain "
                        "valid characters."
                    )
                }
            )

    def save(self, *args, **kwargs):

        if self._state.adding or kwargs.pop(
            "full_clean",
            False,
        ):
            self.full_clean()

        super().save(*args, **kwargs)

    @property
    def value_count(self):

        return self.values.count()

    @property
    def active_value_count(self):

        return self.values.filter(
            is_active=True,
        ).count()

    @property
    def has_values(self):

        return self.values.exists()

    @property
    def has_active_values(self):

        return self.values.filter(
            is_active=True,
        ).exists()

    @property
    def active_values(self):

        return self.values.filter(
            is_active=True,
        )

    @property
    def variant_count(self):

        return (
            self.values
            .filter(variant_values__isnull=False)
            .values("variant_values__variant")
            .distinct()
            .count()
        )