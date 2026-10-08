import uuid

from django.core.exceptions import ValidationError
from django.db import models

from cloudinary.models import CloudinaryField


class ProductCategory(models.Model):
    """
    Global product category used by vendors.

    Categories can be hierarchical.

    Categories belong to the platform rather than to an
    individual vendor.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # ==================================================
    # Identity
    # ==================================================

    name = models.CharField(
        max_length=150,
    )

    slug = models.SlugField(
        max_length=180,
        unique=True,
    )

    # ==================================================
    # Hierarchy
    # ==================================================

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="subcategories",
        null=True,
        blank=True,
    )

    # ==================================================
    # Description
    # ==================================================

    description = models.TextField(
        blank=True,
        default="",
    )

    meta_title = models.CharField(
        max_length=180,
        blank=True,
        default="",
    )

    meta_description = models.CharField(
        max_length=320,
        blank=True,
        default="",
    )

    # ==================================================
    # Display
    # ==================================================

    image = CloudinaryField(
        "image",
        blank=True,
        null=True,
    )

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

        ordering = ["sort_order", "name"]

        constraints = [

            # --------------------------------------------------
            # Unique name under the same parent.
            #
            # Does NOT cover root categories because SQL treats
            # NULL as distinct; the partial constraint below
            # covers the root case.
            # --------------------------------------------------
            models.UniqueConstraint(
                fields=["parent", "name"],
                name="unique_category_name_per_parent",
            ),

            # --------------------------------------------------
            # Unique name across root categories.
            # --------------------------------------------------
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(parent__isnull=True),
                name="unique_root_category_name",
            ),
        ]

        indexes = [

            models.Index(
                fields=["parent", "is_active"],
            ),

            models.Index(
                fields=["is_active", "sort_order"],
            ),
        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):

        if self.parent:
            return f"{self.parent.name} → {self.name}"

        return self.name

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):

        if (
            self.parent_id
            and self.pk
            and self.parent_id == self.pk
        ):

            raise ValidationError(
                {
                    "parent": (
                        "A category cannot be its own "
                        "parent."
                    )
                }
            )

        if not self.parent:
            return

        current = self.parent
        visited = set()

        while current:

            if current.pk in visited:

                raise ValidationError(
                    {
                        "parent": (
                            "Circular category hierarchy "
                            "detected."
                        )
                    }
                )

            visited.add(current.pk)

            if self.pk and current.pk == self.pk:

                raise ValidationError(
                    {
                        "parent": (
                            "A category cannot be an "
                            "ancestor of itself."
                        )
                    }
                )

            current = current.parent

    # ==================================================
    # Save
    # ==================================================

    def save(self, *args, **kwargs):

        if self._state.adding or kwargs.pop(
            "full_clean",
            False,
        ):
            self.full_clean()

        super().save(*args, **kwargs)

    # ==================================================
    # Hierarchy Helpers
    # ==================================================

    @property
    def is_root(self):

        return self.parent_id is None

    @property
    def is_subcategory(self):

        return self.parent_id is not None

    def get_ancestors(self):

        ancestors = []
        visited = set()

        current = self.parent

        while current:

            if current.pk in visited:
                break

            visited.add(current.pk)
            ancestors.append(current)

            current = current.parent

        return ancestors

    @property
    def root_category(self):

        current = self
        visited = set()

        while current.parent:

            if current.pk in visited:
                break

            visited.add(current.pk)

            current = current.parent

        return current

    @property
    def has_children(self):

        return self.subcategories.exists()

    @property
    def product_count(self):

        return self.products.count()

    @property
    def active_product_count(self):

        return self.products.filter(
            is_active=True,
            is_published=True,
        ).count()