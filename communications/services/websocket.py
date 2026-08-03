import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .base import BaseCommunicationService
from .result import CommunicationResult


logger = logging.getLogger(__name__)


class WebSocketService(
    BaseCommunicationService
):

    PROVIDER = "Django Channels"

    @classmethod
    def send(
        cls,
        group,
        event,
        payload,
    ):
        try:

            layer = get_channel_layer()

            async_to_sync(
                layer.group_send
            )(
                group,
                {
                    "type": event,
                    "payload": payload,
                },
            )

            return CommunicationResult.success_result(
                provider=cls.PROVIDER,
            )

        except Exception as exc:

            logger.exception(
                "WebSocket notification failed."
            )

            return CommunicationResult.failure_result(
                provider=cls.PROVIDER,
                message=str(exc),
            )