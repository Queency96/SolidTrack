import uuid

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

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    product = models.ForeignKey(
        "vendors.Product",
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = CloudinaryField(
        "image",
        blank=True,
        null=True,
    )

    alt_text = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    is_primary = models.BooleanField(
        default=False,
    )

    display_order = models.PositiveIntegerField(
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
            "display_order",
            "created_at",
        ]

        indexes = [
            models.Index(
                fields=["product", "is_active"],
            ),
            models.Index(
                fields=["product", "is_primary"],
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="unique_primary_image_per_product",
            ),
        ]

    def __str__(self):

        return (
            f"{self.product} - "
            f"Image {self.pk}"
        )

    def clean(self):

        if self.product_id is None:

            raise ValidationError(
                {
                    "product": (
                        "A product image must belong "
                        "to a product."
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

    @transaction.atomic
    def make_primary(self):
        """
        Make this image the primary image for its product.

        Any existing primary image for the same product
        is automatically demoted.
        """

        (
            ProductImage.objects
            .filter(
                product_id=self.product_id,
                is_primary=True,
            )
            .exclude(pk=self.pk)
            .update(is_primary=False)
        )

        if not self.is_primary:

            self.is_primary = True
            self.save(
                update_fields=[
                    "is_primary",
                    "updated_at",
                ],
            )

        return self