from .models import User
from .models import User, EmailVerification
from .utils import send_verification_email
from .models import PhoneOTP
from .utils import send_sms



class AccountService:

    @staticmethod
    def create_user(validated_data):

        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        verification = EmailVerification.objects.create(
            user=user
        )

        try:
            send_verification_email(
                user,
                verification.token
            )
        except:
            print(user, verification)


        return user



@staticmethod
def send_phone_otp(user):

    PhoneOTP.objects.filter(

        user=user,

        is_used=False

    ).delete()

    otp = PhoneOTP.objects.create(

        user=user

    )

    send_sms(

        user.phone_number,

        otp.code

    )

    return otp