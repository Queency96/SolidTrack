from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
import uuid


class VendorStore(models.Model):
    """
    Physical or operational store belonging to a vendor.

    A vendor can have multiple stores.

    Each product belongs to one selected store, and the
    selected store becomes the pickup location for riders.

    Example:

        Vendor
        │
        ├── Store: Ikeja
        │      ├── Product A
        │      ├── Product B
        │      └── Product C
        │
        ├── Store: Lekki
        │      ├── Product D
        │      └── Product E
        │
        └── Store: Victoria Island
               └── Product F
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # ==================================================
    # Vendor
    # ==================================================

    vendor = models.ForeignKey(
        "vendors.VendorProfile",
        on_delete=models.CASCADE,
        related_name="stores",
    )

    # ==================================================
    # Store Identity
    # ==================================================

    name = models.CharField(
        max_length=255,
    )

    slug = models.SlugField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    # ==================================================
    # Contact
    # ==================================================

    phone = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    email = models.EmailField(
        blank=True,
        default="",
    )

    # ==================================================
    # Address
    # ==================================================

    address_line_1 = models.CharField(
        max_length=255,
    )

    address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    city = models.CharField(
        max_length=100,
    )

    state = models.CharField(
        max_length=100,
    )

    country = models.CharField(
        max_length=100,
        default="Nigeria",
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    # ==================================================
    # Geographic Location
    # ==================================================
    #
    # These coordinates are particularly important for
    # dispatch because this is the rider's pickup point.

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    # ==================================================
    # Store Status
    # ==================================================

    is_active = models.BooleanField(
        default=True,
    )

    is_verified = models.BooleanField(
        default=False,
    )

    # ==================================================
    # Order / Pickup Controls
    # ==================================================

    accepting_orders = models.BooleanField(
        default=True,
    )

    accepting_pickups = models.BooleanField(
        default=True,
    )

    # ==================================================
    # Pickup Information
    # ==================================================

    pickup_instructions = models.TextField(
        blank=True,
        default="",
    )

    # ==================================================
    # Preparation
    # ==================================================

    preparation_time_minutes = (
        models.PositiveIntegerField(
            default=15,
        )
    )

    # ==================================================
    # Store Image
    # ==================================================

    image = models.ImageField(
        upload_to="vendors/stores/",
        blank=True,
        null=True,
    )

    # ==================================================
    # Default Store
    # ==================================================

    is_default = models.BooleanField(
        default=False,
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
            "-is_default",
            "name",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "vendor",
                    "slug",
                ],
                name=(
                    "unique_vendor_store_slug"
                ),
            ),

            models.UniqueConstraint(
                fields=[
                    "vendor",
                ],
                condition=models.Q(
                    is_default=True,
                ),
                name=(
                    "unique_default_store_per_vendor"
                ),
            ),

        ]

        indexes = [

            models.Index(
                fields=[
                    "vendor",
                    "is_active",
                ],
            ),

            models.Index(
                fields=[
                    "latitude",
                    "longitude",
                ],
            ),

            models.Index(
                fields=[
                    "is_active",
                    "accepting_pickups",
                ],
            ),

        ]

    # ==================================================
    # String Representation
    # ==================================================

    def __str__(self):

        return (
            f"{self.vendor} - "
            f"{self.name}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):
        """
        Validate store geographic coordinates.
        """

        if not (
            Decimal("-90")
            <= self.latitude
            <= Decimal("90")
        ):

            raise ValidationError(
                {
                    "latitude": (
                        "Latitude must be between "
                        "-90 and 90."
                    )
                }
            )

        if not (
            Decimal("-180")
            <= self.longitude
            <= Decimal("180")
        ):

            raise ValidationError(
                {
                    "longitude": (
                        "Longitude must be between "
                        "-180 and 180."
                    )
                }
            )

        if (
            self.preparation_time_minutes
            < 0
        ):

            raise ValidationError(
                {
                    "preparation_time_minutes": (
                        "Preparation time cannot "
                        "be negative."
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
    # Pickup Eligibility
    # ==================================================

    @property
    def can_accept_pickup(self):
        """
        Determine whether the store is currently
        configured to accept rider pickups.

        Operating hours are checked separately because
        they depend on the current date/time.
        """

        return (
            self.is_active
            and self.is_verified
            and self.accepting_pickups
        )

    # ==================================================
    # Order Eligibility
    # ==================================================

    @property
    def can_accept_orders(self):

        return (
            self.is_active
            and self.is_verified
            and self.accepting_orders
        )

    # ==================================================
    # Location
    # ==================================================

    @property
    def location(self):
        """
        Return the store coordinates in a normalized
        dictionary structure.

        Useful for dispatch and map integrations.
        """

        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
        }

    # ==================================================
    # Default Store
    # ==================================================

    def make_default(self):
        """
        Make this store the vendor's default store.
        """

        VendorStore.objects.filter(
            vendor=self.vendor,
            is_default=True,
        ).exclude(
            pk=self.pk,
        ).update(
            is_default=False,
        )

        self.is_default = True

        self.save(
            update_fields=[
                "is_default",
                "updated_at",
            ],
        )

        return self