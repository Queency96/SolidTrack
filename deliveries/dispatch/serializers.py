from rest_framework import serializers

from deliveries.constants import DeliveryOfferAction
from deliveries.models.models import (
    DeliveryAssignment,
    DeliveryOffer,
    DispatchConfiguration,
)

from .result import DispatchResult


# ==========================================================
# Delivery Offer Response
# ==========================================================

class DeliveryOfferResponseSerializer(
    serializers.Serializer,
):
    action = serializers.ChoiceField(
        choices=DeliveryOfferAction.choices,
    )

    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def validate(self, attrs):
        if (
            attrs["action"]
            == DeliveryOfferAction.REJECT
            and not attrs.get(
                "rejection_reason"
            )
        ):
            raise serializers.ValidationError(
                {
                    "rejection_reason":
                    (
                        "This field is required "
                        "when rejecting an offer."
                    )
                }
            )

        return attrs


# ==========================================================
# Delivery Offer
# ==========================================================

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
            "delivery",
            "rider",
            "rider_name",
            "status",
            "search_radius",
            "expires_at",
            "responded_at",
            "rejection_reason",
            "created_at",
        )

        read_only_fields = fields


# ==========================================================
# Delivery Assignment
# ==========================================================

class DeliveryAssignmentSerializer(
    serializers.ModelSerializer,
):
    delivery_id = serializers.UUIDField(
        source="delivery.id",
        read_only=True,
    )

    tracking_number = serializers.CharField(
        source="delivery.tracking_number",
        read_only=True,
    )

    rider_id = serializers.UUIDField(
        source="rider.id",
        read_only=True,
    )

    rider_name = serializers.SerializerMethodField()

    rider_phone = serializers.CharField(
        source="rider.phone_number",
        read_only=True,
    )

    assigned_by_id = serializers.UUIDField(
        source="assigned_by.id",
        read_only=True,
    )

    assigned_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryAssignment

        fields = (
            "id",
            "delivery_id",
            "tracking_number",
            "rider_id",
            "rider_name",
            "rider_phone",
            "assigned_by_id",
            "assigned_by_name",
            "status",
            "assigned_at",
            "accepted_at",
            "completed_at",
            "rejected_at",
            "rejection_reason",
            "cancellation_reason",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields

    def get_rider_name(
        self,
        obj,
    ):
        if obj.rider:
            return obj.rider.get_full_name()

        return None

    def get_assigned_by_name(
        self,
        obj,
    ):
        if obj.assigned_by:
            return obj.assigned_by.get_full_name()

        return None


# ==========================================================
# Dispatch Result
# ==========================================================

class DispatchResultSerializer(
    serializers.Serializer,
):
    success = serializers.BooleanField()

    status = serializers.CharField()

    message = serializers.CharField()

    errors = serializers.ListField(
        child=serializers.CharField(),
    )

    warnings = serializers.ListField(
        child=serializers.CharField(),
    )

    data = serializers.DictField()

    assignment = DeliveryAssignmentSerializer(
        read_only=True,
    )

    offer = DeliveryOfferSerializer(
        read_only=True,
    )

    def to_representation(
        self,
        instance: DispatchResult,
    ):
        return {
            "success": instance.success,
            "status": instance.status,
            "message": instance.message,
            "errors": instance.errors,
            "warnings": instance.warnings,
            "data": instance.data,
            "assignment": (
                DeliveryAssignmentSerializer(
                    instance.assignment
                ).data
                if instance.assignment
                else None
            ),
            "offer": (
                DeliveryOfferSerializer(
                    instance.offer
                ).data
                if instance.offer
                else None
            ),
        }


# ==========================================================
# Dispatch Configuration
# ==========================================================

class DispatchConfigurationSerializer(
    serializers.ModelSerializer,
):
    class Meta:
        model = DispatchConfiguration

        fields = "__all__"

        read_only_fields = (
            "created_at",
            "updated_at",
        )
    


class AssignmentActionSerializer(
    serializers.Serializer,
):
    action = serializers.ChoiceField(
        choices=DeliveryAssignment.AssignmentStatus.choices,
    )

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
    )



class DeliveryOfferSerializer(serializers.ModelSerializer):

    rider_name = serializers.CharField(
        source="rider.get_full_name",
        read_only=True,
    )

    delivery_tracking_number = serializers.CharField(
        source="delivery.tracking_number",
        read_only=True,
    )

    class Meta:
        model = DeliveryOffer

        fields = (
            "id",
            "delivery",
            "delivery_tracking_number",
            "rider",
            "rider_name",
            "status",
            "search_radius",
            "expires_at",
            "responded_at",
            "rejection_reason",
            "created_at",
        )