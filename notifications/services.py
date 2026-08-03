import logging

from django.db import transaction

from notifications.models import Notification

from communications.services import (
    EmailService,
    SMSService,
    PushNotificationService,
)


logger = logging.getLogger(__name__)


class NotificationService:
    """
    Central notification service.

    Responsibilities
    ----------------
    • Store notification
    • Send Email
    • Send SMS
    • Send Push Notification

    External channels are dispatched only after the
    current database transaction successfully commits.
    """

    # ==================================================
    # Public API
    # ==================================================

    @classmethod
    def notify(
        cls,
        *,
        user,
        title,
        message,
        notification_type=Notification.NotificationType.SYSTEM,
        data=None,
        send_email=True,
        send_sms=False,
        send_push=True,
        save=True,
    ):
        notification = None

        if save:
            notification = cls._create_notification(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                data=data,
            )

        transaction.on_commit(
            lambda: cls._dispatch(
                user=user,
                title=title,
                message=message,
                data=data,
                send_email=send_email,
                send_sms=send_sms,
                send_push=send_push,
            )
        )

        return notification

    # ==================================================
    # Dispatch Channels
    # ==================================================

    @classmethod
    def _dispatch(
        cls,
        *,
        user,
        title,
        message,
        data,
        send_email,
        send_sms,
        send_push,
    ):
        if send_email:
            cls._safe_send(
                cls._send_email,
                user,
                title,
                message,
            )

        if send_sms:
            cls._safe_send(
                cls._send_sms,
                user,
                message,
            )

        if send_push:
            cls._safe_send(
                cls._send_push,
                user,
                title,
                message,
                data,
            )

    # ==================================================
    # Database
    # ==================================================

    @staticmethod
    def _create_notification(
        *,
        user,
        title,
        message,
        notification_type,
        data,
    ):
        return Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            data=data or {},
        )

    # ==================================================
    # Email
    # ==================================================

    @staticmethod
    def _send_email(
        user,
        subject,
        body,
    ):
        if not user.email:
            return

        EmailService.send_mail(
            recipient=user.email,
            subject=subject,
            body=body,
        )

    # ==================================================
    # SMS
    # ==================================================

    @staticmethod
    def _send_sms(
        user,
        message,
    ):
        phone = getattr(
            user,
            "phone_number",
            None,
        )

        if not phone:
            return

        SMSService.send_sms(
            phone_number=phone,
            message=message,
        )

    # ==================================================
    # Push
    # ==================================================

    @staticmethod
    def _send_push(
        user,
        title,
        body,
        data,
    ):
        PushNotificationService.send(
            user=user,
            title=title,
            body=body,
            data=data or {},
        )

    # ==================================================
    # Safe Sender
    # ==================================================

    @staticmethod
    def _safe_send(
        sender,
        *args,
        **kwargs,
    ):
        """
        Prevent one failed channel from affecting others.
        """
        try:
            sender(
                *args,
                **kwargs,
            )
        except Exception:
            logger.exception(
                "%s notification failed.",
                sender.__name__,
            )