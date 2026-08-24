from django.core.exceptions import ValidationError
from django.db import models


class ProductCategory(models.Model):
    """
    Global product category used by vendors.

    Categories can be hierarchical.

    Example:

        Electronics
        ├── Phones
        │   ├── Smartphones
        │   └── Feature Phones
        │
        ├── Computers
        │   ├── Laptops
        │   └── Desktops
        │
        └── Accessories

        Fashion
        ├── Men's Clothing
        ├── Women's Clothing
        └── Shoes

    Categories belong to the platform rather than to an
    individual vendor.
    """

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

    # ==================================================
    # Display
    # ==================================================

    image = models.ImageField(
        upload_to="product_categories/",
        null=True,
        blank=True,
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

        ordering = [
            "sort_order",
            "name",
        ]

        indexes = [

            models.Index(
                fields=[
                    "parent",
                    "is_active",
                ],
            ),

            models.Index(
                fields=[
                    "is_active",
                    "sort_order",
                ],
            ),

        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):

        if self.parent:

            return (
                f"{self.parent.name} → "
                f"{self.name}"
            )

        return self.name

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):
        """
        Validate category hierarchy.
        """

        # ----------------------------------------------
        # Prevent self-parenting
        # ----------------------------------------------

        if (
            self.parent_id
            and self.pk
            and self.parent_id == self.pk
        ):

            raise ValidationError(
                {
                    "parent": (
                        "A category cannot be "
                        "its own parent."
                    )
                }
            )

        # ----------------------------------------------
        # Prevent circular hierarchy
        # ----------------------------------------------

        if self.parent:

            current = self.parent

            visited = set()

            while current:

                if current.pk in visited:

                    raise ValidationError(
                        {
                            "parent": (
                                "Circular category "
                                "hierarchy detected."
                            )
                        }
                    )

                visited.add(current.pk)

                if (
                    self.pk
                    and current.pk == self.pk
                ):

                    raise ValidationError(
                        {
                            "parent": (
                                "A category cannot "
                                "be an ancestor of "
                                "itself."
                            )
                        }
                    )

                current = current.parent

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
    # Hierarchy Helpers
    # ==================================================

    @property
    def is_root(self):
        """
        Determine whether this is a top-level category.
        """

        return self.parent_id is None

    @property
    def is_subcategory(self):
        """
        Determine whether this category has a parent.
        """

        return self.parent_id is not None

    # ==================================================
    # Ancestors
    # ==================================================

    def get_ancestors(self):
        """
        Return all parent categories from nearest parent
        to the root.
        """

        ancestors = []

        current = self.parent

        while current:

            ancestors.append(
                current,
            )

            current = current.parent

        return ancestors

    # ==================================================
    # Root Category
    # ==================================================

    @property
    def root_category(self):
        """
        Return the highest-level parent category.
        """

        current = self

        while current.parent:

            current = current.parent

        return current

    # ==================================================
    # Children
    # ==================================================

    @property
    def has_children(self):
        """
        Determine whether the category has subcategories.
        """

        return self.subcategories.exists()

    # ==================================================
    # Products
    # ==================================================

    @property
    def product_count(self):
        """
        Return the number of products assigned directly
        to this category.
        """

        return self.products.count()

    # ==================================================
    # Active Products
    # ==================================================

    @property
    def active_product_count(self):
        """
        Return the number of published active products
        assigned directly to this category.
        """

        return self.products.filter(
            is_active=True,
            is_published=True,
        ).count()