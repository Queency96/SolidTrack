from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
import uuid


class CategoryOption(models.Model):
    """
    Defines an option name/template that products in a
    specific category should have.

    This acts as a blueprint — when a product is created
    under a category, ProductOption records are automatically
    created from these templates.

    Example:

        Category: "Smartphones"
            ├── Storage
            ├── RAM
            └── Colour

        Category: "T-Shirts"
            ├── Size
            ├── Colour
            └── Fabric

    Child categories can define their own options and/or
    inherit from parent categories.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # ==================================================
    # Category
    # ==================================================

    category = models.ForeignKey(
        "vendors.ProductCategory",
        on_delete=models.CASCADE,
        related_name="category_options",
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
                    "category",
                    "name",
                ],
                name="unique_category_option_name",
            ),
            models.UniqueConstraint(
                fields=[
                    "category",
                    "slug",
                ],
                name="unique_category_option_slug",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "category",
                    "is_active",
                ],
            ),
            models.Index(
                fields=[
                    "category",
                    "sort_order",
                ],
            ),
        ]

    # ==================================================
    # String Representation
    # ==================================================

    def __str__(self):

        return (
            f"{self.category.name} - "
            f"{self.name}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):
        """
        Validate the option configuration.
        """

        if self.category_id is None:

            raise ValidationError(
                {
                    "category": (
                        "A category option must "
                        "belong to a category."
                    )
                }
            )

        if not self.name or not self.name.strip():

            raise ValidationError(
                {
                    "name": (
                        "Option name cannot "
                        "be empty."
                    )
                }
            )

        if not self.slug or not self.slug.strip():

            raise ValidationError(
                {
                    "slug": (
                        "Option slug cannot "
                        "be empty."
                    )
                }
            )

        self.name = self.name.strip()
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
    # Properties
    # ==================================================

    @property
    def is_inherited(self):
        """
        Determine whether this option is inherited
        from a parent category.
        """

        return self.category.parent_id is not None