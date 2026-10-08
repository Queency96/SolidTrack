from decimal import Decimal
import uuid
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from common.constant import (
    NIGERIA_STATE_CHOICES,
    VALID_STATE_CODES,
    normalize_state,
)


class VendorStore(models.Model):
    """
    Physical or operational store belonging to a vendor.

    A vendor may operate multiple stores. Each store is a
    distinct pickup location and can be independently set
    as the vendor's default store.
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

    # --------------------------------------------------
    # State code for product scoping.
    #
    # Kept in sync with `state` by clean(). Indexed because
    # product browsing filters on this column.
    # --------------------------------------------------
    state_code = models.CharField(
        max_length=2,
        choices=NIGERIA_STATE_CHOICES,
        blank=True,
        default="",
        db_index=True,
        help_text=(
            "ISO 3166-2:NG state code. Auto-derived from `state`."
        ),
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

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[
            MinValueValidator(Decimal("-90")),
            MaxValueValidator(Decimal("90")),
        ],
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[
            MinValueValidator(Decimal("-180")),
            MaxValueValidator(Decimal("180")),
        ],
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

    pickup_instructions = models.TextField(
        blank=True,
        default="",
    )

    # ==================================================
    # Preparation
    # ==================================================

    preparation_time_minutes = models.PositiveIntegerField(
        default=15,
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

        ordering = ["-is_default", "name"]

        constraints = [

            models.UniqueConstraint(
                fields=["vendor", "slug"],
                name="unique_vendor_store_slug",
            ),

            models.UniqueConstraint(
                fields=["vendor"],
                condition=models.Q(is_default=True),
                name="unique_default_store_per_vendor",
            ),
        ]

        indexes = [

            models.Index(
                fields=["vendor", "is_active"],
            ),

            models.Index(
                fields=["latitude", "longitude"],
            ),

            models.Index(
                fields=["is_active", "accepting_pickups"],
            ),

            models.Index(
                fields=["state_code", "is_active"],
            ),
        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):

        return f"{self.vendor} - {self.name}"

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):

        # --------------------------------------------------
        # Derive state_code from state when either is present.
        # --------------------------------------------------

        if self.state:

            derived_code = normalize_state(self.state)

            if derived_code:
                self.state_code = derived_code

        if (
            self.state_code
            and self.state_code not in VALID_STATE_CODES
        ):

            raise ValidationError(
                {
                    "state_code": (
                        f"'{self.state_code}' is not a "
                        "valid Nigerian state code."
                    )
                }
            )

        if self.state and self.state_code:

            expected = normalize_state(self.state)

            if (
                expected
                and expected != self.state_code
            ):

                raise ValidationError(
                    {
                        "state_code": (
                            f"state_code "
                            f"'{self.state_code}' does "
                            f"not match state "
                            f"'{self.state}'."
                        )
                    }
                )

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
    # Pickup Eligibility
    # ==================================================

    @property
    def can_accept_pickup(self):

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

        return {
            "latitude": float(self.latitude),
            "longitude": float(self.longitude),
        }

    # ==================================================
    # Default Store
    # ==================================================

    def make_default(self):

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