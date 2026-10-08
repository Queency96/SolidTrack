"""
Rider-facing OTP verification serializers.
"""

from rest_framework import serializers


class RiderVerifyOTPRequestSerializer(serializers.Serializer):
    """
    Input for POST /api/rider/orders/<uuid>/verify-otp/.
    """

    otp = serializers.CharField(
        max_length=10,
        min_length=4,
        allow_blank=False,
        trim_whitespace=True,
    )

    def validate_otp(self, value):
        value = value.strip()

        if not value.isdigit():
            raise serializers.ValidationError(
                "OTP must contain only digits."
            )

        return value


class RiderVerifyOTPResultSerializer(serializers.Serializer):
    """
    Output for the verify endpoint.
    """

    success = serializers.BooleanField()
    message = serializers.CharField()
    order_status = serializers.CharField(allow_null=True)
    delivered_at = serializers.DateTimeField(allow_null=True)