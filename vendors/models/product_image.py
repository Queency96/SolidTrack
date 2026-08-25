from django.core.exceptions import ValidationError
from django.db import models, transaction
from cloudinary.models import CloudinaryField


class ProductImage(models.Model):
    """
    Image belonging to a product.

    A product can have multiple images.

    Example:

        Product
            ├── Main Image
            ├── Front Image
            ├── Back Image
            ├── Side Image
            └── Detail Image

    The first/primary image can be used as the
    product thumbnail throughout the marketplace.
    """

    # ==================================================
    # Product
    # ==================================================

    product = models.ForeignKey(
        "vendors.Product",
        on_delete=models.CASCADE,
        related_name="images",
    )

    # ==================================================
    # Image
    # ==================================================

    image = CloudinaryField(
        "image",
        blank=True,
        null=True,
    )

    # ==================================================
    # Image Information
    # ==================================================

    alt_text = models.CharField(
        max_length=255,
        blank=True,
    )

    # ==================================================
    # Primary Image
    # ==================================================

    is_primary = models.BooleanField(
        default=False,
    )

    # ==================================================
    # Ordering
    # ==================================================

    display_order = models.PositiveIntegerField(
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
            "display_order",
            "created_at",
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
                    "is_primary",
                ],
            ),

        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "product",
                ],
                condition=models.Q(
                    is_primary=True,
                ),
                name=(
                    "unique_primary_image_per_product"
                ),
            ),

        ]

    # ==================================================
    # String Representation
    # ==================================================

    def __str__(self):

        return (
            f"{self.product} - "
            f"Image {self.pk}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):
        """
        Validate product image ownership and state.
        """

        if self.product_id is None:
            raise ValidationError(
                {
                    "product": (
                        "A product image must belong "
                        "to a product."
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
    # Primary Image Helper
    # ==================================================
    def make_primary(self):
        """
        Make this image the primary image for its product.

        Any existing primary image for the same product
        is automatically demoted.
        """

        with transaction.atomic():

            ProductImage.objects.filter(
                product=self.product,
                is_primary=True,
            ).exclude(
                pk=self.pk,
            ).update(
                is_primary=False,
            )

            self.is_primary = True

            self.save(
                update_fields=[
                    "is_primary",
                    "updated_at",
                ],
            )

        return self