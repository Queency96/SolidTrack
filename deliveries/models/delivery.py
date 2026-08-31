from decimal import Decimal
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from common.models import TimeStampedModel
from riders.models import RiderProfile


class Delivery(TimeStampedModel):
    """
    Represents the transportation of one OrderFulfillment
    from a VendorStore to the customer's destination.

    Architecture:

        Order
          ↓
        OrderFulfillment
          ├── OrderItem[]
          ├── Package[]
          └── Delivery
                  ├── DeliveryAddress[]
                  ├── Assignment
                  └── Rider / Dispatch

    Delivery is strictly a logistics entity.

    Commercial responsibility belongs to Order and
    OrderFulfillment.

    Delivery is responsible for:

        - route
        - transportation requirements
        - delivery status
        - delivery pricing
        - scheduling
        - tracking
    """

    # ==================================================
    # Delivery Type
    # ==================================================

    class DeliveryType(models.TextChoices):

        INSTANT = (
            "INSTANT",
            "Instant",
        )

        SCHEDULED = (
            "SCHEDULED",
            "Scheduled",
        )

    # ==================================================
    # Delivery Status
    # ==================================================

    class DeliveryStatus(models.TextChoices):

        PENDING = (
            "PENDING",
            "Pending",
        )

        WAITING_FOR_RIDER = (
            "WAITING_FOR_RIDER",
            "Waiting for Rider",
        )

        RIDER_ASSIGNED = (
            "RIDER_ASSIGNED",
            "Rider Assigned",
        )

        RIDER_ACCEPTED = (
            "RIDER_ACCEPTED",
            "Rider Accepted",
        )

        PICKED_UP = (
            "PICKED_UP",
            "Picked Up",
        )

        IN_TRANSIT = (
            "IN_TRANSIT",
            "In Transit",
        )

        DELIVERED = (
            "DELIVERED",
            "Delivered",
        )

        CANCELLED = (
            "CANCELLED",
            "Cancelled",
        )

        FAILED = (
            "FAILED",
            "Failed",
        )

    # ==================================================
    # Payment Status
    # ==================================================

    class PaymentStatus(models.TextChoices):

        PENDING = (
            "PENDING",
            "Pending",
        )

        PAID = (
            "PAID",
            "Paid",
        )

        REFUNDED = (
            "REFUNDED",
            "Refunded",
        )

    # ==================================================
    # ID
    # ==================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # ==================================================
    # Tracking
    # ==================================================

    tracking_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        db_index=True,
    )

    # ==================================================
    # Fulfillment
    # ==================================================

    fulfillment = models.OneToOneField(
        "order.OrderFulfillment",
        on_delete=models.PROTECT,
        related_name="delivery",
    )

    # ==================================================
    # Parties
    # ==================================================

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="deliveries",
    )

    vendor = models.ForeignKey(
        "vendors.VendorProfile",
        on_delete=models.PROTECT,
        related_name="deliveries",
        null=True,
        blank=True,
    )

    pickup_store = models.ForeignKey(
        "vendors.VendorStore",
        on_delete=models.PROTECT,
        related_name="deliveries",
        null=True,
        blank=True,
    )

    # ==================================================
    # Pickup Store Snapshot
    # ==================================================

    pickup_store_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    # ==================================================
    # Delivery Type
    # ==================================================

    delivery_type = models.CharField(
        max_length=20,
        choices=DeliveryType.choices,
    )

    # ==================================================
    # Status
    # ==================================================

    status = models.CharField(
        max_length=30,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True,
    )

    # ==================================================
    # Payment
    # ==================================================

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )

    # ==================================================
    # Delivery Requirements
    # ==================================================

    vehicle_type = models.CharField(
        max_length=20,
        choices=RiderProfile.VehicleType.choices,
        null=True,
        blank=True,
    )

    # ==================================================
    # Package Summary
    # ==================================================
    #
    # These are snapshots calculated from the packages
    # belonging to the fulfillment.
    #
    # They allow pricing and dispatch to work without
    # repeatedly aggregating package records.
    #

    total_package_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text="Total package weight in kilograms.",
    )

    package_count = models.PositiveIntegerField(
        default=0,
    )

    # ==================================================
    # Route
    # ==================================================

    distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    estimated_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    # ==================================================
    # Scheduling
    # ==================================================

    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    # ==================================================
    # Pricing
    # ==================================================

    estimated_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    actual_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    base_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    distance_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    weight_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    surge_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    insurance_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    service_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    currency = models.CharField(
        max_length=3,
        default="NGN",
    )

    # ==================================================
    # Notes
    # ==================================================

    notes = models.TextField(
        blank=True,
        default="",
    )

    # ==================================================
    # Lifecycle Timestamps
    # ==================================================

    waiting_for_rider_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rider_assigned_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rider_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    picked_up_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    in_transit_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    failed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        ordering = [
            "-created_at",
        ]

        indexes = [

            models.Index(
                fields=[
                    "status",
                ],
            ),

            models.Index(
                fields=[
                    "payment_status",
                ],
            ),

            models.Index(
                fields=[
                    "customer",
                ],
            ),

            models.Index(
                fields=[
                    "vendor",
                ],
            ),

            models.Index(
                fields=[
                    "pickup_store",
                ],
            ),

            models.Index(
                fields=[
                    "scheduled_at",
                ],
            ),

            models.Index(
                fields=[
                    "status",
                    "scheduled_at",
                ],
            ),

            models.Index(
                fields=[
                    "vendor",
                    "status",
                ],
            ),

            models.Index(
                fields=[
                    "pickup_store",
                    "status",
                ],
            ),
        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):

        return self.tracking_number

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):

        # ----------------------------------------------
        # Fulfillment
        # ----------------------------------------------

        if self.fulfillment_id is None:

            raise ValidationError(
                {
                    "fulfillment": (
                        "A delivery must belong "
                        "to an order fulfillment."
                    )
                }
            )
            

        # ----------------------------------------------
        # Customer
        # ----------------------------------------------

        if (
            self.customer_id
            != self.fulfillment.order.customer_id
        ):

            raise ValidationError(
                {
                    "customer": (
                        "Delivery customer must "
                        "match the fulfillment "
                        "order customer."
                    )
                }
            )

        # ----------------------------------------------
        # Pick-up Store
        # ----------------------------------------------

        if (
            self.pickup_store_id
            != self.fulfillment.store_id
        ):

            raise ValidationError(
                {
                    "pickup_store": (
                        "Pickup store must match "
                        "the fulfillment store."
                    )
                }
            )

        # ----------------------------------------------
        # Vendor
        # ----------------------------------------------

        if (
            self.vendor_id
            != self.fulfillment.store.vendor_id
        ):

            raise ValidationError(
                {
                    "vendor": (
                        "Delivery vendor must "
                        "match the fulfillment "
                        "store vendor."
                    )
                }
            )

        # ----------------------------------------------
        # Delivery Type
        # ----------------------------------------------

        if (
            self.delivery_type
            == self.DeliveryType.SCHEDULED
            and self.scheduled_at is None
        ):

            raise ValidationError(
                {
                    "scheduled_at": (
                        "Scheduled delivery "
                        "requires a scheduled "
                        "date and time."
                    )
                }
            )

        # ----------------------------------------------
        # Instant Delivery
        # ----------------------------------------------

        if (
            self.delivery_type
            == self.DeliveryType.INSTANT
            and self.scheduled_at is not None
        ):

            raise ValidationError(
                {
                    "scheduled_at": (
                        "Instant delivery must "
                        "not have a scheduled time."
                    )
                }
            )

        # ----------------------------------------------
        # Distance
        # ----------------------------------------------

        if (
            self.distance_km is not None
            and self.distance_km < Decimal("0.00")
        ):

            raise ValidationError(
                {
                    "distance_km": (
                        "Distance cannot "
                        "be negative."
                    )
                }
            )

        # ----------------------------------------------
        # Package Weight
        # ----------------------------------------------

        if (
            self.total_package_weight
            < Decimal("0.000")
        ):

            raise ValidationError(
                {
                    "total_package_weight": (
                        "Total package weight "
                        "cannot be negative."
                    )
                }
            )

        # ----------------------------------------------
        # Package Count
        # ----------------------------------------------

        if self.package_count < 0:

            raise ValidationError(
                {
                    "package_count": (
                        "Package count cannot "
                        "be negative."
                    )
                }
            )

        # ----------------------------------------------
        # Pricing
        # ----------------------------------------------

        monetary_fields = [
            "estimated_price",
            "actual_price",
            "base_price",
            "distance_price",
            "weight_price",
            "surge_price",
            "discount",
            "insurance_fee",
            "service_fee",
            "total_price",
        ]

        for field_name in monetary_fields:

            value = getattr(
                self,
                field_name,
            )

            if value < Decimal("0.00"):

                raise ValidationError(
                    {
                        field_name: (
                            f"{field_name.replace('_', ' ').capitalize()} "
                            "cannot be negative."
                        )
                    }
                )

        # ----------------------------------------------
        # Total Price
        # ----------------------------------------------

        calculated_total = (
            self.base_price
            + self.distance_price
            + self.weight_price
            + self.surge_price
            + self.insurance_fee
            + self.service_fee
            - self.discount
        )

        if calculated_total < Decimal("0.00"):

            calculated_total = Decimal("0.00")

        if self.total_price != calculated_total:

            raise ValidationError(
                {
                    "total_price": (
                        "Delivery total price does "
                        "not match the pricing "
                        "breakdown."
                    )
                }
            )

        # ----------------------------------------------
        # Status Timestamps
        # ----------------------------------------------

        timestamp_requirements = {

            self.DeliveryStatus.WAITING_FOR_RIDER:
                "waiting_for_rider_at",

            self.DeliveryStatus.RIDER_ASSIGNED:
                "rider_assigned_at",

            self.DeliveryStatus.RIDER_ACCEPTED:
                "rider_accepted_at",

            self.DeliveryStatus.PICKED_UP:
                "picked_up_at",

            self.DeliveryStatus.IN_TRANSIT:
                "in_transit_at",

            self.DeliveryStatus.DELIVERED:
                "delivered_at",

            self.DeliveryStatus.CANCELLED:
                "cancelled_at",

            self.DeliveryStatus.FAILED:
                "failed_at",
        }

        required_field = timestamp_requirements.get(
            self.status
        )

        if (
            required_field
            and getattr(
                self,
                required_field,
            ) is None
        ):

            raise ValidationError(
                {
                    required_field: (
                        f"{required_field.replace('_', ' ').capitalize()} "
                        f"is required when delivery status "
                        f"is {self.status}."
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

        if not self.tracking_number:

            self.tracking_number = (
                f"DLV-"
                f"{uuid.uuid4().hex[:12].upper()}"
            )

        self.full_clean()

        super().save(
            *args,
            **kwargs,
        )

    # ==================================================
    # Properties
    # ==================================================

    @property
    def is_pending(self):

        return (
            self.status
            == self.DeliveryStatus.PENDING
        )

    @property
    def is_waiting_for_rider(self):

        return (
            self.status
            == self.DeliveryStatus.WAITING_FOR_RIDER
        )

    @property
    def is_assigned(self):

        return self.status in [

            self.DeliveryStatus.RIDER_ASSIGNED,

            self.DeliveryStatus.RIDER_ACCEPTED,

            self.DeliveryStatus.PICKED_UP,

            self.DeliveryStatus.IN_TRANSIT,

            self.DeliveryStatus.DELIVERED,
        ]

    @property
    def is_picked_up(self):

        return self.status in [

            self.DeliveryStatus.PICKED_UP,

            self.DeliveryStatus.IN_TRANSIT,

            self.DeliveryStatus.DELIVERED,
        ]

    @property
    def is_in_transit(self):

        return self.status in [

            self.DeliveryStatus.IN_TRANSIT,

            self.DeliveryStatus.DELIVERED,
        ]

    @property
    def is_delivered(self):

        return (
            self.status
            == self.DeliveryStatus.DELIVERED
        )

    @property
    def is_cancelled(self):

        return (
            self.status
            == self.DeliveryStatus.CANCELLED
        )

    @property
    def is_terminal(self):

        return self.status in [

            self.DeliveryStatus.DELIVERED,

            self.DeliveryStatus.CANCELLED,

            self.DeliveryStatus.FAILED,
        ]

    # ==================================================
    # Address Helpers
    # ==================================================

    @property
    def pickup_address(self):

        return self.addresses.filter(
            address_type="PICKUP",
        ).first()

    @property
    def destination_address(self):

        return self.addresses.filter(
            address_type="DELIVERY",
        ).first()

    # ==================================================
    # Location Helpers
    # ==================================================

    @property
    def pickup_location(self):

        address = self.pickup_address

        if not address:
            return None

        return {
            "latitude": address.latitude,
            "longitude": address.longitude,
        }

    @property
    def destination_location(self):

        address = self.destination_address

        if not address:
            return None

        return {
            "latitude": address.latitude,
            "longitude": address.longitude,
        }

    @property
    def route(self):

        return {
            "pickup": self.pickup_location,
            "destination": self.destination_location,
            "distance_km": self.distance_km,
            "estimated_duration_minutes": (
                self.estimated_duration_minutes
            ),
        }