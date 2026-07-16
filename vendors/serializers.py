from rest_framework import serializers
from .models import VendorProfile


class VendorProfileSerializer(serializers.ModelSerializer):

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
    )

    class Meta:

        model = VendorProfile

        exclude = (
            "verification_status",
            "created_at",
            "updated_at",
            "user",
        )

    def update(self, instance, validated_data):

        user_data = validated_data.pop(
            "user",
            {},
        )

        for key, value in user_data.items():
            setattr(
                instance.user,
                key,
                value,
            )

        instance.user.save()

        for key, value in validated_data.items():
            setattr(
                instance,
                key,
                value,
            )

        instance.save()

        return instance