from django.conf import settings
from django.core.mail import send_mail


def send_verification_email(user, token):

    verification_url = (
        f"{settings.FRONTEND_URL}"
        f"/verify-email/{token}/"
    )

    subject = "Verify Your Email"

    message = f"""
Hello {user.first_name},

Welcome to our delivery platform.

Please verify your email by clicking the link below.

{verification_url}

This link expires in 24 hours.

If you did not create this account, ignore this email.
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )



def send_sms(phone_number, otp):

    """
    Placeholder for SMS provider integration.

    Future providers:

    - Termii
    - Twilio
    - Africa's Talking
    - Infobip

    """

    print(
        f"OTP for {phone_number}: {otp}"
    )


