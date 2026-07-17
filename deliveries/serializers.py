from rest_framework import serializers

from .models import (
    Delivery,
    DeliveryAddress,
    Package,
)


class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress

        exclude = (
            "id",
            "delivery",
            "created_at",
            "updated_at",
        )




class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package

        exclude = (
            "id",
            "delivery",
            "created_at",
            "updated_at",
        )



class DeliveryBookingSerializer(serializers.ModelSerializer):
    package = PackageSerializer()

    pickup = DeliveryAddressSerializer(
        write_only=True
    )

    destination = DeliveryAddressSerializer(
        write_only=True
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
        choices=Package.PackageSize.choices
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
        ]
    )

    delivery_type = serializers.ChoiceField(
        choices=Delivery.DeliveryType.choices
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


from deliveries.constants import DeliveryOfferAction


class DeliveryOfferResponseSerializer(serializers.Serializer):
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