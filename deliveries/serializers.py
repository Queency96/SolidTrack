from rest_framework import serializers

from .models import (
    Delivery,
    DeliveryAddress,
    Package,
    DeliveryOffer,
    DeliveryAssignment,
)

from deliveries.constants import DeliveryOfferAction


# ============================================================
# Delivery Address
# ============================================================

class DeliveryAddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = DeliveryAddress
        exclude = (
            "id",
            "delivery",
            "created_at",
            "updated_at",
        )


# ============================================================
# Package
# ============================================================

class PackageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Package
        exclude = (
            "id",
            "delivery",
            "created_at",
            "updated_at",
        )


# ============================================================
# Delivery Booking
# ============================================================

class DeliveryBookingSerializer(serializers.ModelSerializer):

    package = PackageSerializer()

    pickup = DeliveryAddressSerializer(
        write_only=True,
    )

    destination = DeliveryAddressSerializer(
        write_only=True,
    )

    class Meta:
        model = Delivery

        fields = (
            "delivery_type",
            "scheduled_at",
            "notes",
            "estimated_price",
            "package",
            "pickup",
            "destination",
        )

    def validate(self, attrs):

        if (
            attrs["delivery_type"]
            == Delivery.DeliveryType.SCHEDULED
            and not attrs.get("scheduled_at")
        ):
            raise serializers.ValidationError(
                {
                    "scheduled_at":
                    "Scheduled deliveries require a date."
                }
            )

        return attrs


# ============================================================
# Delivery
# ============================================================

class DeliverySerializer(serializers.ModelSerializer):

    package = serializers.SerializerMethodField()

    pickup = serializers.SerializerMethodField()

    destination = serializers.SerializerMethodField()

    class Meta:

        model = Delivery

        fields = (
            "id",
            "tracking_number",
            "status",
            "delivery_type",
            "scheduled_at",
            "estimated_price",
            "notes",
            "package",
            "pickup",
            "destination",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields

    def get_package(self, obj):

        package = getattr(obj, "package", None)

        if not package:
            return None

        return PackageSerializer(package).data

    def get_pickup(self, obj):

        address = obj.addresses.filter(
            address_type=DeliveryAddress.AddressType.PICKUP,
        ).first()

        if not address:
            return None

        return DeliveryAddressSerializer(address).data

    def get_destination(self, obj):

        address = obj.addresses.filter(
            address_type=DeliveryAddress.AddressType.DELIVERY,
        ).first()

        if not address:
            return None

        return DeliveryAddressSerializer(address).data


# ============================================================
# Delivery Assignment
# ============================================================

class DeliveryAssignmentSerializer(
    serializers.ModelSerializer,
):

    rider_name = serializers.CharField(
        source="rider.get_full_name",
        read_only=True,
    )

    rider_phone = serializers.CharField(
        source="rider.phone_number",
        read_only=True,
    )

    class Meta:

        model = DeliveryAssignment

        fields = (
            "id",
            "status",
            "assigned_at",
            "accepted_at",
            "completed_at",
            "rejected_at",
            "rejection_reason",
            "cancellation_reason",
            "rider_name",
            "rider_phone",
        )

        read_only_fields = fields


# ============================================================
# Delivery Offer
# ============================================================

class DeliveryOfferSerializer(
    serializers.ModelSerializer,
):

    rider_name = serializers.CharField(
        source="rider.get_full_name",
        read_only=True,
    )

    class Meta:

        model = DeliveryOffer

        fields = (
            "id",
            "status",
            "search_radius",
            "expires_at",
            "responded_at",
            "rejection_reason",
            "rider_name",
        )

        read_only_fields = fields


# ============================================================
# Price Estimate
# ============================================================

class PriceEstimateSerializer(serializers.Serializer):

    pickup_latitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    pickup_longitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    destination_latitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    destination_longitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    package_size = serializers.ChoiceField(
        choices=Package.PackageSize.choices,
    )

    weight = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    vehicle_type = serializers.ChoiceField(
        choices=[
            "BIKE",
            "CAR",
            "VAN",
            "TRUCK",
        ],
    )

    delivery_type = serializers.ChoiceField(
        choices=Delivery.DeliveryType.choices,
    )

    declared_value = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        default=0,
    )

    insurance = serializers.BooleanField(
        default=False,
    )


# ============================================================
# Delivery Offer Response
# ============================================================

class DeliveryOfferResponseSerializer(
    serializers.Serializer,
):

    action = serializers.ChoiceField(
        choices=DeliveryOfferAction.CHOICES,
    )

    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def validate(self, attrs):

        if (
            attrs["action"]
            == DeliveryOfferAction.REJECT
            and not attrs.get("rejection_reason")
        ):
            raise serializers.ValidationError(
                {
                    "rejection_reason":
                    "This field is required."
                }
            )

        return attrs


# ============================================================
# Dispatch Result
# ============================================================

class DispatchResultSerializer(
    serializers.Serializer,
):
    success = serializers.BooleanField()

    status = serializers.CharField()

    message = serializers.CharField()

    delivery = DeliverySerializer(
        read_only=True,
        allow_null=True,
    )

    assignment = DeliveryAssignmentSerializer(
        read_only=True,
        allow_null=True,
    )

    offer = DeliveryOfferSerializer(
        read_only=True,
        allow_null=True,
    )

    errors = serializers.ListField(
        child=serializers.CharField(),
    )

    warnings = serializers.ListField(
        child=serializers.CharField(),
    )

    data = serializers.DictField()

    def to_representation(self, instance):

        return {
            "success": instance.success,
            "status": instance.status,
            "message": instance.message,
            "delivery": DeliverySerializer(
                instance.delivery
            ).data if instance.delivery else None,
            "assignment": DeliveryAssignmentSerializer(
                instance.assignment
            ).data if instance.assignment else None,
            "offer": DeliveryOfferSerializer(
                instance.offer
            ).data if instance.offer else None,
            "errors": instance.errors,
            "warnings": instance.warnings,
            "data": instance.data,
        }