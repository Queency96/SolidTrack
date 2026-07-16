from rest_framework import serializers
from .models import RiderProfile


class RiderProfileSerializer(serializers.ModelSerializer):

    first_name = serializers.CharField(
        source="user.first_name"
    )

    last_name = serializers.CharField(
        source="user.last_name"
    )

    email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    phone_number = serializers.CharField(
        source="user.phone_number"
    )

    profile_picture = serializers.ImageField(
        source="user.profile_picture",
        required=False,
        allow_null=True,
    )

    class Meta:

        model = RiderProfile

        fields = (
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "profile_picture",
            "vehicle_type",
            "vehicle_plate_number",
            "driver_license",
            "nin",
        )

        extra_kwargs = {
            "driver_license": {
                "required": False,
                "allow_null": True,
            },
            "vehicle_type": {
                "required": False,
            },
            "vehicle_plate_number": {
                "required": False,
            },
            "nin": {
                "required": False,
            },
        }

    def update(self, instance, validated_data):

        user_data = validated_data.pop("user", {})

        for attr, value in user_data.items():
            setattr(instance.user, attr, value)

        instance.user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        return instance