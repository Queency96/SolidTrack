import logging

from .base import BaseCommunicationService
from .result import CommunicationResult


logger = logging.getLogger(__name__)


class PushNotificationService(
    BaseCommunicationService
):

    PROVIDER = "Firebase"

    @classmethod
    def send(
        cls,
        user,
        title,
        body,
        data=None,
    ):
        try:

            #
            # firebase_admin.messaging.send(...)
            #

            return CommunicationResult.success_result(
                provider=cls.PROVIDER,
            )

        except Exception as exc:

            logger.exception(
                "Push notification failed."
            )

            return CommunicationResult.failure_result(
                provider=cls.PROVIDER,
                message=str(exc),
            )