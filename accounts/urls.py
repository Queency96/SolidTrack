from django.urls import path
from rest_framework_simplejwt.views import (TokenRefreshView)
from .views import (LoginView, LogoutView, CurrentUserView, RegisterCustomerView, RegisterVendor_Rider_Admin_View, RegisterRiderView, VerifyEmailView, ResendVerificationEmailView, SendPhoneOTPView, VerifyPhoneView)
from .admin_views import (ApproveVendorView, RejectVendorView, ApproveRiderView, RejectRiderView)

urlpatterns = [
  path ("login/", LoginView.as_view(), name="login"),
  path ("logout/", LogoutView.as_view(), name="logout"),
  path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
  path("me/", CurrentUserView.as_view(), name="current_user"),
  path("register/customer/", RegisterCustomerView.as_view(), name="register"),
  path("register/vendor-rider-admin/", RegisterVendor_Rider_Admin_View.as_view(), name="vendor-rider-admin-register"),
  path("verify-email/<str:token>/", VerifyEmailView.as_view(), name="verify_email"),
  path("resend-verification-email/", ResendVerificationEmailView.as_view(), name="resend_verification_email"),
  path("send-phone-otp/", SendPhoneOTPView.as_view(), name="send_phone_otp"),
  path("verify-phone/", VerifyPhoneView.as_view(), name="verify_phone"),



  # Admin Routes
  path("vendors/<uuid:pk>/approve/", ApproveVendorView.as_view(),),
  path("vendors/<uuid:pk>/reject/", RejectVendorView.as_view(),),
  path("riders/<uuid:pk>/approve/", ApproveRiderView.as_view(),),
  path("riders/<uuid:pk>/reject/", RejectRiderView.as_view(),),

]