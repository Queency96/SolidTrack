from django.core.exceptions import ValidationError
from django.db import models
from cloudinary.models import CloudinaryField
import uuid




class ProductVariantImage(models.Model):
    """
    Image belonging specifically to a ProductVariant.

    This allows each variant to have its own images.

    Example:

        Product:
            iPhone 17

        Variant:
            Black / 128GB
                ├── Front
                ├── Back
                └── Side

            White / 256GB
                ├── Front
                ├── Back
                └── Side

    ProductImage is used for the general product gallery.

    ProductVariantImage is used when an image is specific
    to a particular variant.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # ==================================================
    # Variant
    # ==================================================

    variant = models.ForeignKey(
        "vendors.ProductVariant",
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
        default="",
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
                    "variant",
                    "is_active",
                ],
            ),

            models.Index(
                fields=[
                    "variant",
                    "is_primary",
                ],
            ),

        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "variant",
                ],
                condition=models.Q(
                    is_primary=True,
                ),
                name=(
                    "unique_primary_image_per_variant"
                ),
            ),

        ]

    # ==================================================
    # String Representation
    # ==================================================

    def __str__(self):

        return (
            f"{self.variant} - "
            f"Image {self.pk}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):
        """
        Validate variant image configuration.
        """

        # ----------------------------------------------
        # Variant
        # ----------------------------------------------

        if self.variant_id is None:

            raise ValidationError(
                {
                    "variant": (
                        "A variant image must "
                        "belong to a product variant."
                    )
                }
            )

        # ----------------------------------------------
        # Image
        # ----------------------------------------------

        if not self.image:

            raise ValidationError(
                {
                    "image": (
                        "A variant image file "
                        "is required."
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
    # Primary Image
    # ==================================================

    def make_primary(self):
        """
        Make this image the primary image for
        its variant.

        Any existing primary image belonging to
        the same variant is demoted first.
        """

        ProductVariantImage.objects.filter(
            variant=self.variant,
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

    # ==================================================
    # Active
    # ==================================================

    @property
    def is_available(self):
        """
        Determine whether this image should currently
        be displayed.
        """

        return (
            self.is_active
            and self.variant.is_available
        )

    # ==================================================
    # Variant
    # ==================================================

    @property
    def product(self):
        """
        Return the product associated with this
        variant image.
        """

        return self.variant.product

    # ==================================================
    # Product ID
    # ==================================================

    @property
    def product_id(self):
        """
        Return the parent product ID.
        """

        return self.variant.product_id

    # ==================================================
    # Pickup Store
    # ==================================================

    @property
    def pickup_store(self):
        """
        Return the store associated with this variant.
        """

        return self.variant.pickup_store

    # ==================================================
    # Pickup Location
    # ==================================================

    @property
    def pickup_location(self):
        """
        Return the pickup location associated with
        this variant.
        """

        return self.variant.pickup_location
