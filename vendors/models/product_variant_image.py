from django.core.exceptions import ValidationError
from django.db import models, transaction
from cloudinary.models import CloudinaryField
import uuid


class ProductVariantImage(models.Model):
    """
    Image belonging specifically to a ProductVariant.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    variant = models.ForeignKey(
        "vendors.ProductVariant",
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = CloudinaryField("image", blank=True, null=True)

    alt_text = models.CharField(max_length=255, blank=True, default="")

    is_primary = models.BooleanField(default=False)

    display_order = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:

        ordering = ["display_order", "created_at"]

        indexes = [
            models.Index(fields=["variant", "is_active"]),
            models.Index(fields=["variant", "is_primary"]),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["variant"],
                condition=models.Q(is_primary=True),
                name="unique_primary_image_per_variant",
            ),
        ]

    def __str__(self):
        return f"{self.variant} - Image {self.pk}"

    def clean(self):

        if self.variant_id is None:
            raise ValidationError(
                {"variant": "A variant image must belong to a product variant."}
            )

        if not self.image:
            raise ValidationError(
                {"image": "A variant image file is required."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @transaction.atomic
    def make_primary(self):
        """
        Make this image the primary image for its variant.

        Atomic so the demote-existing-then-promote-self sequence
        cannot interleave with another concurrent call.
        """

        ProductVariantImage.objects.filter(
            variant=self.variant,
            is_primary=True,
        ).exclude(pk=self.pk).update(is_primary=False)

        self.is_primary = True
        self.save(update_fields=["is_primary", "updated_at"])

        return self

    @property
    def is_available(self):
        return self.is_active and self.variant.is_available

    @property
    def product(self):
        return self.variant.product

    @property
    def product_id(self):
        return self.variant.product_id

    @property
    def pickup_store(self):
        return self.variant.pickup_store

    @property
    def pickup_location(self):
        return self.variant.pickup_location