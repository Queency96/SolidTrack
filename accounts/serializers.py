from django.contrib.auth import authenticate
from .services import AccountService
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True
    )

    def validate(self, attrs):
        email = attrs["email"]
        password = attrs["password"]

        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("Account is disabled.")

        refresh = RefreshToken.for_user(user)

        attrs["user"] = user
        attrs["access"] = str(refresh.access_token)
        attrs["refresh"] = str(refresh)

        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "role",
            "profile_picture",
            "is_email_verified",
            "is_phone_verified",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    confirm_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    role = serializers.ChoiceField(
        choices=User.Roles.choices,
        default=User.Roles.CUSTOMER
    )

    class Meta:
        model = User

        fields = [
            # "first_name",
            # "last_name",
            "email",
            "phone_number",
            "password",
            "confirm_password",
            "role",
        ]

        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
            "email": {"required": True},
            "phone_number": {"required": True},
        }

    def validate_email(self, value):
        value = value.lower().strip()

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Email already exists."
            )

        return value

    def validate_phone_number(self, value):
        value = value.strip()

        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                "Phone number already exists."
            )

        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters."
            )

        if not any(char.isupper() for char in value):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter."
            )

        if not any(char.islower() for char in value):
            raise serializers.ValidationError(
                "Password must contain at least one lowercase letter."
            )

        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError(
                "Password must contain at least one number."
            )

        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {
                    "confirm_password": "Passwords do not match."
                }
            )

        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")

        return AccountService.create_user(validated_data)


class VerifyPhoneSerializer(serializers.Serializer):

    otp = serializers.CharField(
        max_length=6
    )



class SendPhoneOTPSerializer(serializers.Serializer):

    phone_number = serializers.CharField(
        max_length=15
    )

    def validate_phone_number(self, value):
        value = value.strip()

        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                "Phone number already exists."
            )

        return value
    


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


