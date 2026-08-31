from rest_framework import serializers
from deliveries.constants import DeliveryOfferAction
from deliveries.models import (
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
    """
    Validate a rider's response to a delivery offer.
    """

    action = serializers.ChoiceField(
        choices=DeliveryOfferAction.choices,
    )

    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    def validate(
        self,
        attrs,
    ):
        action = attrs.get(
            "action",
        )

        rejection_reason = (
            attrs.get(
                "rejection_reason",
            )
            or ""
        ).strip()

        # ----------------------------------------------
        # Reject requires a reason
        # ----------------------------------------------

        if (
            action
            == DeliveryOfferAction.REJECT
            and not rejection_reason
        ):
            raise serializers.ValidationError(
                {
                    "rejection_reason": (
                        "This field is required "
                        "when rejecting an offer."
                    ),
                },
            )

        # ----------------------------------------------
        # Ignore reason for ACCEPT
        # ----------------------------------------------

        if (
            action
            == DeliveryOfferAction.ACCEPT
        ):
            attrs["rejection_reason"] = ""

        else:
            attrs["rejection_reason"] = (
                rejection_reason
            )

        return attrs


# ==========================================================
# Delivery Offer
# ==========================================================

class DeliveryOfferSerializer(
    serializers.ModelSerializer,
):
    """
    Read-only representation of a DeliveryOffer.
    """

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

        read_only_fields = fields


# ==========================================================
# Delivery Assignment
# ==========================================================

class DeliveryAssignmentSerializer(
    serializers.ModelSerializer,
):
    """
    Read-only representation of a DeliveryAssignment.
    """

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

    # ------------------------------------------------------
    # Rider Name
    # ------------------------------------------------------

    def get_rider_name(
        self,
        obj,
    ):
        rider = getattr(
            obj,
            "rider",
            None,
        )

        if rider is None:
            return None

        return rider.get_full_name()

    # ------------------------------------------------------
    # Assigned By Name
    # ------------------------------------------------------

    def get_assigned_by_name(
        self,
        obj,
    ):
        assigned_by = getattr(
            obj,
            "assigned_by",
            None,
        )

        if assigned_by is None:
            return None

        return assigned_by.get_full_name()


# ==========================================================
# Dispatch Result
# ==========================================================

class DispatchResultSerializer(
    serializers.Serializer,
):
    """
    Serializer for DispatchResult.

    DispatchResult itself is not a Django model, therefore
    custom representation is used.
    """

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
        allow_null=True,
    )

    offer = DeliveryOfferSerializer(
        read_only=True,
        allow_null=True,
    )

    def to_representation(
        self,
        instance,
    ):
        if not isinstance(
            instance,
            DispatchResult,
        ):
            raise TypeError(
                "DispatchResultSerializer expects "
                "a DispatchResult instance."
            )

        # ----------------------------------------------
        # Status
        # ----------------------------------------------

        status_value = instance.status

        if hasattr(
            status_value,
            "value",
        ):
            status_value = status_value.value

        # ----------------------------------------------
        # Assignment
        # ----------------------------------------------

        assignment_data = None

        if instance.assignment is not None:
            assignment_data = (
                DeliveryAssignmentSerializer(
                    instance.assignment,
                    context=self.context,
                ).data
            )

        # ----------------------------------------------
        # Offer
        # ----------------------------------------------

        offer_data = None

        if instance.offer is not None:
            offer_data = (
                DeliveryOfferSerializer(
                    instance.offer,
                    context=self.context,
                ).data
            )

        # ----------------------------------------------
        # Base response
        # ----------------------------------------------

        return {
            "success": instance.success,

            "status": str(
                status_value,
            ),

            "message": instance.message,

            "errors": list(
                instance.errors,
            ),

            "warnings": list(
                instance.warnings,
            ),

            "data": dict(
                instance.data,
            ),

            "assignment": assignment_data,

            "offer": offer_data,
        }


# ==========================================================
# Dispatch Configuration
# ==========================================================

class DispatchConfigurationSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for dispatch configuration.

    This serializer is primarily intended for
    administrative configuration.
    """

    class Meta:
        model = DispatchConfiguration

        fields = "__all__"

        read_only_fields = (
            "created_at",
            "updated_at",
        )


# ==========================================================
# Assignment Action
# ==========================================================

class AssignmentActionSerializer(
    serializers.Serializer,
):
    """
    Assignment management actions.

    These actions are intentionally separate from
    AssignmentStatus values.
    """

    action = serializers.ChoiceField(
        choices=(
            (
                "CANCEL",
                "Cancel assignment",
            ),
        ),
    )

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    def validate(
        self,
        attrs,
    ):
        if (
            attrs["action"] == "CANCEL"
            and not attrs.get("reason")
        ):
            raise serializers.ValidationError(
                {
                    "reason": (
                        "A cancellation reason "
                        "is required."
                    ),
                },
            )

        return attrs