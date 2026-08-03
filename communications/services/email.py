import logging

from django.conf import settings
from django.core.mail import send_mail

from .base import BaseCommunicationService
from .result import CommunicationResult


logger = logging.getLogger(__name__)


class EmailService(BaseCommunicationService):

    PROVIDER = "SMTP"

    @classmethod
    def send_mail(
        cls,
        recipient,
        subject,
        body,
        html_message=None,
    ):
        try:

            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                html_message=html_message,
                fail_silently=False,
            )

            return CommunicationResult.success_result(
                provider=cls.PROVIDER,
            )

        except Exception as exc:

            logger.exception(
                "Email sending failed."
            )

            return CommunicationResult.failure_result(
                provider=cls.PROVIDER,
                message=str(exc),
            )

    @classmethod
    def send(
        cls,
        **kwargs,
    ):
        return cls.send_mail(**kwargs)