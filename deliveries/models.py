
from django.utils import timezone
import uuid
from django.conf import settings
from django.db import models
from common.models import TimeStampedModel
from decimal import Decimal
from riders.models import RiderProfile



class Delivery(TimeStampedModel):

    # ==================================================
    # Delivery Type
    # ==================================================

    class DeliveryType(models.TextChoices):
        INSTANT = "INSTANT", "Instant"
        SCHEDULED = "SCHEDULED", "Scheduled"

    # ==================================================
    # Delivery Status
    # ==================================================

    class DeliveryStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
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
        PICKED_UP = "PICKED_UP", "Picked Up"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"
        FAILED = "FAILED", "Failed"

    # ==================================================
    # Payment Status
    # ==================================================

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        REFUNDED = "REFUNDED", "Refunded"

    # ==================================================
    # Identity
    # ==================================================

    tracking_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
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

    # ==================================================
    # Delivery Type / Status
    # ==================================================

    delivery_type = models.CharField(
        max_length=20,
        choices=DeliveryType.choices,
    )

    status = models.CharField(
        max_length=30,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True,
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )

    # ==================================================
    # Pickup
    # ==================================================
    #
    # These fields are a SNAPSHOT of the vendor's
    # store location at the time the delivery is created.
    #
    # Do not allow the customer to arbitrarily provide
    # the pickup location for vendor deliveries.
    #

    pickup_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    pickup_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    pickup_address = models.TextField()

    # ==================================================
    # Destination
    # ==================================================

    destination_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    destination_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    destination_address = models.TextField()

    # ==================================================
    # Delivery Requirements
    # ==================================================

    vehicle_type = models.CharField(
        max_length=20,
        choices=RiderProfile.VehicleType.choices,
        null=True,
        blank=True,
    )

    package_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    package_size = models.CharField(
        max_length=30,
        blank=True,
    )

    # ==================================================
    # Scheduling
    # ==================================================

    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ==================================================
    # Pricing
    # ==================================================

    estimated_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    actual_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    base_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    distance_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    weight_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    surge_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    insurance_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    service_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    # ==================================================
    # Notes
    # ==================================================

    notes = models.TextField(
        blank=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["status"],
            ),
            models.Index(
                fields=["payment_status"],
            ),
            models.Index(
                fields=["vendor"],
            ),
            models.Index(
                fields=["customer"],
            ),
        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):
        return self.tracking_number

    # ==================================================
    # Save
    # ==================================================

    def save(self, *args, **kwargs):

        if not self.tracking_number:
            self.tracking_number = (
                f"DLV-{uuid.uuid4().hex[:10].upper()}"
            )

        super().save(*args, **kwargs)


class DeliveryAssignment(TimeStampedModel):
    class AssignmentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ASSIGNED = "ASSIGNED", "Assigned"
        ACCEPTED = "ACCEPTED", "Accepted"
        EN_ROUTE_PICKUP = "EN_ROUTE_PICKUP", "En Route to Pickup"
        ARRIVED_PICKUP = "ARRIVED_PICKUP", "Arrived at Pickup"
        PICKED_UP = "PICKED_UP", "Picked Up"
        OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
        ARRIVED_DESTINATION = (
            "ARRIVED_DESTINATION",
            "Arrived at Destination",
        )
        COMPLETED = "COMPLETED", "Completed"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    is_active = models.BooleanField(
        default=True,
    )

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delivery_assignments",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assigned_deliveries",
        help_text="Admin or system that assigned the rider.",
    )

    status = models.CharField(
        max_length=30,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.PENDING,
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejected_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejection_reason = models.TextField(
        blank=True,
    )

    cancellation_reason = models.TextField(
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-assigned_at"]

        indexes = [
            models.Index(
                fields=["delivery", "status"],
            ),
            models.Index(
                fields=["rider", "status"],
            ),
            models.Index(
                fields=["status"],
            ),
            models.Index(
                fields=["assigned_at"],
            ),
            models.Index(
                fields=["is_active"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.delivery.tracking_number} "
            f"→ {self.rider.get_full_name() or self.rider.email}"
        )



class DeliveryAddress(TimeStampedModel):
    class AddressType(models.TextChoices):
        PICKUP = "PICKUP", "Pickup"
        DELIVERY = "DELIVERY", "Delivery"

    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="addresses",
    )

    address_type = models.CharField(
        max_length=20,
        choices=AddressType.choices,
    )

    contact_name = models.CharField(max_length=255)

    contact_phone = models.CharField(max_length=20)

    address = models.TextField()

    city = models.CharField(max_length=100)

    state = models.CharField(max_length=100)

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    landmark = models.CharField(
        max_length=255,
        blank=True,
    )

    def __str__(self):
        return f"{self.address_type} - {self.address}"




class Package(TimeStampedModel):
    class PackageSize(models.TextChoices):
        SMALL = "SMALL", "Small"
        MEDIUM = "MEDIUM", "Medium"
        LARGE = "LARGE", "Large"

    class PackageCategory(models.TextChoices):
        DOCUMENT = "DOCUMENT", "Document"
        FOOD = "FOOD", "Food"
        ELECTRONICS = "ELECTRONICS", "Electronics"
        CLOTHING = "CLOTHING", "Clothing"
        MEDICAL = "MEDICAL", "Medical"
        OTHER = "OTHER", "Other"

    delivery = models.OneToOneField(
        Delivery,
        on_delete=models.CASCADE,
        related_name="package",
    )

    package_name = models.CharField(
        max_length=255,
    )

    package_category = models.CharField(
        max_length=30,
        choices=PackageCategory.choices,
    )

    package_size = models.CharField(
        max_length=20,
        choices=PackageSize.choices,
    )

    weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    fragile = models.BooleanField(
        default=False,
    )

    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    photo = models.ImageField(
        upload_to="packages/",
        blank=True,
        null=True,
    )

    description = models.TextField(blank=True)

    def __str__(self):
        return self.package_name



class PricingConfiguration(TimeStampedModel):

    class VehicleType(models.TextChoices):
        BIKE = "BIKE", "Bike"
        CAR = "CAR", "Car"
        VAN = "VAN", "Van"
        TRUCK = "TRUCK", "Truck"

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Example: Lagos Default Pricing",
    )

    # -----------------------
    # Base Pricing
    # -----------------------

    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1000,
    )

    price_per_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=250,
    )

    service_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=300,
    )

    insurance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0100"),  # 1%
        help_text="Decimal percentage (0.01 = 1%)",
    )

    # -----------------------
    # Package Pricing
    # -----------------------

    small_package_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    medium_package_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=300,
    )

    large_package_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=700,
    )

    # -----------------------
    # Vehicle Multipliers
    # -----------------------

    bike_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
    )

    car_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.35,
    )

    van_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.80,
    )

    truck_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.50,
    )

    # -----------------------
    # Surge
    # -----------------------

    enable_surge = models.BooleanField(
        default=False,
    )

    surge_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.50,
    )

    # -----------------------
    # Status
    # -----------------------

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name







class DispatchConfiguration(TimeStampedModel):
    """
    Global dispatch configuration.

    Only one active configuration should exist.
    """

    # ==================================================
    # Dispatch Strategy
    # ==================================================

    class DispatchStrategy(models.TextChoices):
        BALANCED = (
            "BALANCED",
            "Balanced",
        )

        NEAREST = (
            "NEAREST",
            "Nearest Rider",
        )

        PERFORMANCE = (
            "PERFORMANCE",
            "Performance Based",
        )

        VENDOR_PRIORITY = (
            "VENDOR_PRIORITY",
            "Vendor Priority",
        )

        CUSTOMER_PRIORITY = (
            "CUSTOMER_PRIORITY",
            "Customer Priority",
        )

        FAIR_DISTRIBUTION = (
            "FAIR_DISTRIBUTION",
            "Fair Distribution",
        )

        EXPRESS = (
            "EXPRESS",
            "Express Delivery",
        )

    # ==================================================
    # Identity
    # ==================================================

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    dispatch_strategy = models.CharField(
        max_length=30,
        choices=DispatchStrategy.choices,
        default=DispatchStrategy.BALANCED,
        help_text=(
            "Determines how riders are ranked "
            "during dispatch."
        ),
    )

    # ==================================================
    # Search Radius
    # ==================================================

    initial_search_radius_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=3,
    )

    maximum_search_radius_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15,
    )

    search_radius_increment_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2,
    )

    # ==================================================
    # Rider Response
    # ==================================================

    rider_response_timeout_seconds = (
        models.PositiveIntegerField(
            default=30,
        )
    )

    max_assignment_attempts = (
        models.PositiveSmallIntegerField(
            default=5,
        )
    )

    auto_redispatch = models.BooleanField(
        default=True,
    )

    # ==================================================
    # Matching Rules
    # ==================================================

    minimum_rider_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=3.50,
    )

    maximum_active_deliveries = (
        models.PositiveSmallIntegerField(
            default=2,
        )
    )

    # ==================================================
    # Dispatch Scoring Weights
    # ==================================================

    rating_weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=10,
    )

    distance_weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=2,
    )

    workload_weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=5,
    )

    acceptance_rate_weight = (
        models.DecimalField(
            max_digits=6,
            decimal_places=2,
            default=4,
        )
    )

    completion_rate_weight = (
        models.DecimalField(
            max_digits=6,
            decimal_places=2,
            default=3,
        )
    )

    cancellation_weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=8,
        help_text=(
            "Penalty applied to riders with "
            "higher cancellation rates."
        ),
    )

    experience_weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=2,
    )

    # ==================================================
    # Dispatch Behaviour
    # ==================================================

    offer_batch_size = (
        models.PositiveSmallIntegerField(
            default=1,
            help_text=(
                "Number of riders offered "
                "a delivery simultaneously."
            ),
        )
    )

    # ==================================================
    # Scheduling
    # ==================================================

    allow_scheduled_dispatch = (
        models.BooleanField(
            default=True,
        )
    )

    dispatch_before_pickup_minutes = (
        models.PositiveIntegerField(
            default=15,
        )
    )

    # ==================================================
    # Status
    # ==================================================

    is_active = models.BooleanField(
        default=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:
        ordering = (
            "-created_at",
        )

    # ==================================================
    # String Representation
    # ==================================================

    def __str__(self):
        return self.name
        


class DeliveryOffer(TimeStampedModel):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    # ==================================================
    # Relationships
    # ==================================================

    delivery = models.ForeignKey(
        "Delivery",
        on_delete=models.CASCADE,
        related_name="offers",
    )

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="delivery_offers",
    )

    # ==================================================
    # Offer State
    # ==================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # ==================================================
    # Dispatch Information
    # ==================================================

    search_radius = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    # ==================================================
    # Timestamps
    # ==================================================

    offered_at = models.DateTimeField(
        auto_now_add=True,
    )

    responded_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    expires_at = models.DateTimeField()

    # ==================================================
    # Response
    # ==================================================

    rejection_reason = models.TextField(
        blank=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:
        ordering = (
            "-offered_at",
        )

        indexes = [
            models.Index(
                fields=[
                    "delivery",
                    "status",
                ],
            ),
            models.Index(
                fields=[
                    "rider",
                    "status",
                ],
            ),
            models.Index(
                fields=[
                    "expires_at",
                ],
            ),
        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):
        rider_name = (
            self.rider.get_full_name()
            or self.rider.email
        )

        return (
            f"{self.delivery.tracking_number} → "
            f"{rider_name}"
        )


class DeliveryTimeline(TimeStampedModel):
    class EventType(models.TextChoices):
        CREATED = "CREATED", "Created"
        SEARCHING_RIDERS = (
            "SEARCHING_RIDERS",
            "Searching Riders",
        )
        OFFER_SENT = (
            "OFFER_SENT",
            "Offer Sent",
        )
        OFFER_ACCEPTED = (
            "OFFER_ACCEPTED",
            "Offer Accepted",
        )
        OFFER_REJECTED = (
            "OFFER_REJECTED",
            "Offer Rejected",
        )
        OFFER_EXPIRED = (
            "OFFER_EXPIRED",
            "Offer Expired",
        )
        ASSIGNED = (
            "ASSIGNED",
            "Assigned",
        )
        RIDER_ARRIVED = (
            "RIDER_ARRIVED",
            "Rider Arrived",
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

    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="timeline",
    )

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    event = models.CharField(
        max_length=50,
        choices=EventType.choices,
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    occurred_at = models.DateTimeField(
        default=timezone.now,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="delivery_timeline_events",
    )
    class Meta:
        ordering = [
            "-occurred_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "delivery",
                    "occurred_at",
                ]
            ),
        ]
    def __str__(self):
        return (
            f"{self.delivery.tracking_number}"
            f" - {self.title}"
        )


class AssignmentAction(models.TextChoices):

    ACCEPT = "accept", "Accept"

    START_PICKUP = (
        "start_pickup",
        "Start Pickup",
    )

    ARRIVE_PICKUP = (
        "arrive_pickup",
        "Arrive Pickup",
    )

    PICKUP_COMPLETED = (
        "pickup_completed",
        "Pickup Completed",
    )

    START_DELIVERY = (
        "start_delivery",
        "Start Delivery",
    )

    ARRIVE_DESTINATION = (
        "arrive_destination",
        "Arrive Destination",
    )

    COMPLETE = (
        "complete",
        "Complete",
    )

    CANCEL = (
        "cancel",
        "Cancel",
    )

    REASSIGN = (
        "reassign",
        "Reassign",
    )




class DispatchHistory(TimeStampedModel):
    """
    Immutable audit trail for the dispatch lifecycle.

    Every important dispatch transition should create
    one history record.
    """

    class EventType(models.TextChoices):
        DELIVERY_CREATED = (
            "DELIVERY_CREATED",
            "Delivery Created",
        )
        DISPATCH_STARTED = (
            "DISPATCH_STARTED",
            "Dispatch Started",
        )
        OFFER_CREATED = (
            "OFFER_CREATED",
            "Offer Created",
        )
        OFFER_ACCEPTED = (
            "OFFER_ACCEPTED",
            "Offer Accepted",
        )
        OFFER_REJECTED = (
            "OFFER_REJECTED",
            "Offer Rejected",
        )
        OFFER_EXPIRED = (
            "OFFER_EXPIRED",
            "Offer Expired",
        )
        OFFER_CANCELLED = (
            "OFFER_CANCELLED",
            "Offer Cancelled",
        )
        RIDER_ASSIGNED = (
            "RIDER_ASSIGNED",
            "Rider Assigned",
        )
        ASSIGNMENT_ACCEPTED = (
            "ASSIGNMENT_ACCEPTED",
            "Assignment Accepted",
        )
        PICKUP_STARTED = (
            "PICKUP_STARTED",
            "Pickup Started",
        )
        ARRIVED_PICKUP = (
            "ARRIVED_PICKUP",
            "Arrived Pickup",
        )
        PICKUP_COMPLETED = (
            "PICKUP_COMPLETED",
            "Pickup Completed",
        )
        DELIVERY_STARTED = (
            "DELIVERY_STARTED",
            "Delivery Started",
        )
        ARRIVED_DESTINATION = (
            "ARRIVED_DESTINATION",
            "Arrived Destination",
        )
        DELIVERY_COMPLETED = (
            "DELIVERY_COMPLETED",
            "Delivery Completed",
        )
        ASSIGNMENT_CANCELLED = (
            "ASSIGNMENT_CANCELLED",
            "Assignment Cancelled",
        )
        ASSIGNMENT_REASSIGNED = (
            "ASSIGNMENT_REASSIGNED",
            "Assignment Reassigned",
        )
        DISPATCH_FAILED = (
            "DISPATCH_FAILED",
            "Dispatch Failed",
        )

    delivery = models.ForeignKey(
        "deliveries.Delivery",
        on_delete=models.CASCADE,
        related_name="dispatch_history",
    )

    assignment = models.ForeignKey(
        "deliveries.DeliveryAssignment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatch_history",
    )

    offer = models.ForeignKey(
        "deliveries.DeliveryOffer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatch_history",
    )

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatch_history",
    )

    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices,
    )

    status = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    message = models.TextField(
        blank=True,
        default="",
    )

    reason = models.TextField(
        blank=True,
        default="",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = ("created_at",)

        indexes = [
            models.Index(
                fields=[
                    "delivery",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "event_type",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "rider",
                    "created_at",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.delivery} - "
            f"{self.event_type}"
        )