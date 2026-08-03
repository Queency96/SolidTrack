import logging

from .base import BaseCommunicationService
from .result import CommunicationResult


logger = logging.getLogger(__name__)


class SMSService(BaseCommunicationService):

    PROVIDER = "Termii"

    @classmethod
    def send_sms(
        cls,
        phone_number,
        message,
    ):
        try:

            #
            # Call Termii API here
            #

            return CommunicationResult.success_result(
                provider=cls.PROVIDER,
            )

        except Exception as exc:

            logger.exception(
                "SMS sending failed."
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
        return cls.send_sms(**kwargs)