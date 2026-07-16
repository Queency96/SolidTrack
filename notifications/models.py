from django.db import models
from django.conf import settings
from common.models import TimeStampedModel
import uuid

class Notification(TimeStampedModel):
    class NotificationType(models.TextChoices):
        DELIVERY = "DELIVERY", "Delivery"
        PAYMENT = "PAYMENT", "Payment"
        WALLET = "WALLET", "Wallet"
        SYSTEM = "SYSTEM", "System"
        PROMOTION = "PROMOTION", "Promotion"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM
    )

    title = models.CharField(
        max_length=255
    )

    message = models.TextField()

    is_read = models.BooleanField(
        default=False
    )

    data = models.JSONField(
        blank=True,
        null=True
    )
    def __str__(self):
        return self.title