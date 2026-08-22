from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from .models import User, EmailVerification
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    VerifyPhoneSerializer,
    LogoutSerializer,
)
from .services import (
    AccountService,
    PhoneOTP,
    send_verification_email,
)



class RegisterCustomerView(GenericAPIView):
    permission_classes = []
    serializer_class = RegisterSerializer
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(role=User.Roles.CUSTOMER)
        return Response(
            {
                "success": True,
                "message": "Customer registration successful.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )



class RegisterVendor_Rider_Admin_View(GenericAPIView):
    permission_classes = []
    serializer_class = RegisterSerializer
    def post(self, request, *args, **kwargs):
        ROLE = self.request['role']  # Assuming the role is passed in the request data
        if not ROLE:
            return Response(
                "Chose a role"
            )
            
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            {
                "success": True,
                "message": "Registration successful.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class RegisterRiderView(GenericAPIView):
    permission_classes = []
    serializer_class = RegisterSerializer
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save(role=User.Roles.RIDER)

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "success": True,
                "message": "Rider registration successful.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )



class LoginView(GenericAPIView):
    permission_classes = []
    serializer_class = LoginSerializer
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        return Response(
            {
                "success": True,
                "message": "Login successful.",
                "access": data["access"],
                "refresh": data["refresh"],
                "user": UserSerializer(data["user"]).data,
            },
            status=status.HTTP_200_OK,
        )



@extend_schema(request=None)
class CurrentUserView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        return Response(UserSerializer(request.user).data)



class LogoutView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = RefreshToken(serializer.validated_data["refresh"])
        token.blacklist()

        return Response(
            {
                "success": True,
                "message": "Logout successful.",
            }
        )



@extend_schema(request=None)
class VerifyEmailView(GenericAPIView):
    permission_classes = []
    def get(self, request, token, *args, **kwargs):
        try:
            email_verification = EmailVerification.objects.get(token=token)
        except EmailVerification.DoesNotExist:
            return Response({"success": False, "message": "Invalid token."})

        if email_verification.is_expired():
            return Response({"success": False, "message": "Token expired."})

        email_verification.user.is_active = True
        email_verification.user.save()

        email_verification.is_used = True
        email_verification.save()

        return Response({"success": True, "message": "Email verified."})


@extend_schema(request=None)
class ResendVerificationEmailView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        if request.user.is_email_verified:
            return Response(
                {
                    "success": False,
                    "message": "Email already verified.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        EmailVerification.objects.filter(
            user=request.user,
            is_used=False,
        ).delete()

        verification = EmailVerification.objects.create(
            user=request.user,
        )

        send_verification_email(
            request.user,
            verification.token,
        )

        return Response(
            {
                "success": True,
                "message": "Verification email sent.",
            }
        )


@extend_schema(request=None)
class SendPhoneOTPView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        if request.user.is_phone_verified:
            return Response(
                {
                    "success": False,
                    "message": "Phone already verified.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        AccountService.send_phone_otp(request.user)

        return Response(
            {
                "success": True,
                "message": "OTP sent successfully.",
            }
        )



class VerifyPhoneView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VerifyPhoneSerializer
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp = serializer.validated_data["otp"]

        try:
            phone_otp = PhoneOTP.objects.get(
                user=request.user,
                code=otp,
                is_used=False,
            )
        except PhoneOTP.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Invalid OTP.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if phone_otp.is_expired():
            return Response(
                {
                    "success": False,
                    "message": "OTP expired.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.is_phone_verified = True
        request.user.save(update_fields=["is_phone_verified"])

        phone_otp.is_used = True
        phone_otp.save(update_fields=["is_used"])

        return Response(
            {
                "success": True,
                "message": "Phone verified.",
            }
        )


