from rest_framework import serializers
from deliveries.models import DeliveryAssignment




class DeliveryOfferResponseSerializer(serializers.Serializer):
    class ActionChoices:
        ACCEPT = "accept"
        REJECT = "reject"

    ACTION_CHOICES = (
        (ActionChoices.ACCEPT, "Accept"),
        (ActionChoices.REJECT, "Reject"),
    )
    action = serializers.ChoiceField(
        choices=ACTION_CHOICES,
    )
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    def validate(self, attrs):
        action = attrs["action"]
        if (
            action == self.ActionChoices.REJECT
            and not attrs.get("rejection_reason")
        ):
            raise serializers.ValidationError(
                {
                    "rejection_reason":
                    "This field is required when rejecting an offer."
                }
            )
        return attrs



class DeliveryAssignmentSerializer(serializers.ModelSerializer):
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
            "assigned_at",
            "accepted_at",
            "rejected_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_rider_name(self, obj):
        if obj.rider:
            return obj.rider.get_full_name()
        return None

    def get_assigned_by_name(self, obj):
        if obj.assigned_by:
            return obj.assigned_by.get_full_name()
        return None