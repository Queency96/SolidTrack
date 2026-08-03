import logging

from django.conf import settings
import requests

from .base import BaseCommunicationService
from .result import CommunicationResult


logger = logging.getLogger(__name__)


class WhatsAppService(BaseCommunicationService):
    """
    WhatsApp communication service.

    Default implementation uses the Meta
    WhatsApp Cloud API.

    Can later be replaced with Twilio,
    Termii, Infobip, etc., without changing
    NotificationService.
    """

    PROVIDER = "WhatsApp Cloud API"

    API_VERSION = "v21.0"

    @classmethod
    def send_message(
        cls,
        phone_number,
        message,
    ):
        """
        Send a plain text WhatsApp message.
        """

        url = (
            f"https://graph.facebook.com/"
            f"{cls.API_VERSION}/"
            f"{settings.WHATSAPP_PHONE_NUMBER_ID}"
            f"/messages"
        )

        headers = {
            "Authorization": (
                f"Bearer "
                f"{settings.WHATSAPP_ACCESS_TOKEN}"
            ),
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {
                "body": message,
            },
        }

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30,
            )

            response.raise_for_status()

            return CommunicationResult.success_result(
                provider=cls.PROVIDER,
                response=response.json(),
            )

        except Exception as exc:

            logger.exception(
                "WhatsApp message failed."
            )

            return CommunicationResult.failure_result(
                provider=cls.PROVIDER,
                message=str(exc),
            )

    @classmethod
    def send_template(
        cls,
        phone_number,
        template_name,
        language="en",
        components=None,
    ):
        """
        Send an approved WhatsApp template.
        """

        url = (
            f"https://graph.facebook.com/"
            f"{cls.API_VERSION}/"
            f"{settings.WHATSAPP_PHONE_NUMBER_ID}"
            f"/messages"
        )

        headers = {
            "Authorization": (
                f"Bearer "
                f"{settings.WHATSAPP_ACCESS_TOKEN}"
            ),
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language,
                },
                "components": components or [],
            },
        }

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30,
            )

            response.raise_for_status()

            return CommunicationResult.success_result(
                provider=cls.PROVIDER,
                response=response.json(),
            )

        except Exception as exc:

            logger.exception(
                "WhatsApp template failed."
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
        """
        Generic interface used by
        NotificationService.
        """

        if "template_name" in kwargs:
            return cls.send_template(**kwargs)

        return cls.send_message(**kwargs)