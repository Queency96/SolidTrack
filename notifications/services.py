from .models import Notification


class NotificationService:

    @staticmethod
    def create_notification(
        user,
        title,
        message,
        notification_type=Notification.NotificationType.SYSTEM,
        data=None,
    ):

        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            data=data or {},
        )

        # Future:
        # Firebase Push
        # Email
        # SMS
        # WebSocket

        return notification