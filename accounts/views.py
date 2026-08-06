from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.services import AccountService, PhoneOTP, send_verification_email
from .serializers import RegisterSerializer, VerifyPhoneSerializer
from django.utils import timezone
from .models import EmailVerification
from .serializers import (
    LoginSerializer,
    UserSerializer,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import RegisterSerializer, UserSerializer


class RegisterCustomerView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(role=User.Roles.CUSTOMER)
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "success": True,
                "message": "Customer registration successful.",
                # "access": str(refresh.access_token),
                # "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class RegisterVendor_Rider_Admin_View(APIView):
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "success": True,
                "message": "Vendor registration successful.",
                # "access": str(refresh.access_token),
                # "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class RegisterRiderView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
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


class LoginView(APIView):

    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        return Response(
            {
                "success": True,
                "message": "Login successful.",
                "access": data["access"],
                "refresh": data["refresh"],
                "user": UserSerializer(
                    data["user"]
                ).data,
            },
            status=status.HTTP_200_OK
        )



class CurrentUserView(APIView):
    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):
        serializer = UserSerializer(
            request.user
        )

        return Response(
            serializer.data
        )
  

class LogoutView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def post(self, request):

        try:

            refresh_token = request.data.get(
                "refresh"
            )

            token = RefreshToken(
                refresh_token
            )

            token.blacklist()

            return Response(
                {
                    "success": True,
                    "message": "Logout successful."
                }
            )

        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "Invalid token."
                },
                status=400
            )


class VerifyEmailView(APIView):

    permission_classes = []

    def get(self, request, token):

        try:

            verification = EmailVerification.objects.get(
                token=token
            )

        except EmailVerification.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "Invalid verification link."
                },
                status=400
            )

        if verification.is_used:

            return Response(
                {
                    "success": False,
                    "message": "Verification link has already been used."
                },
                status=400
            )

        if verification.is_expired():

            return Response(
                {
                    "success": False,
                    "message": "Verification link has expired."
                },
                status=400
            )

        verification.user.is_email_verified = True
        verification.user.save()

        verification.is_used = True
        verification.save()

        return Response(
            {
                "success": True,
                "message": "Email verified successfully."
            }
        )



class ResendVerificationEmailView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        if request.user.is_email_verified:

            return Response(
                {
                    "message": "Email already verified."
                }
            )

        EmailVerification.objects.filter(
            user=request.user,
            is_used=False
        ).delete()

        verification = EmailVerification.objects.create(
            user=request.user
        )

        send_verification_email(
            request.user,
            verification.token
        )

        return Response(
            {
                "success": True,
                "message": "Verification email sent."
            }
        )



class SendPhoneOTPView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if request.user.is_phone_verified:
            return Response({
                "message":
                "Phone already verified."
            })

        AccountService.send_phone_otp(
            request.user
        )

        return Response({
            "success": True,
            "message":
            "OTP sent successfully."
        })


class VerifyPhoneView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = VerifyPhoneSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        otp = serializer.validated_data["otp"]

        try:
            phone_otp = PhoneOTP.objects.get(
                user=request.user,
                code=otp,
                is_used=False
            )

        except PhoneOTP.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message":
                    "Invalid OTP."
                },
                status=400
            )

        if phone_otp.is_expired():
            return Response(
                {
                    "success": False,
                    "message":
                    "OTP expired."
                },
                status=400
            )

        request.user.is_phone_verified = True
        request.user.save()
        phone_otp.is_used = True
        phone_otp.save()

        return Response(
            {
                "success": True,
                "message":
                "Phone verified."
            }
        )






