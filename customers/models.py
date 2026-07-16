from django.db import models
from django.conf import settings
from common.models import TimeStampedModel
import uuid

class CustomerProfile(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile"
    )
    referral_code = models.CharField(
        max_length=20,
        unique=True
    )
    referred_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals"
    )
    default_pickup_address = models.TextField(
        blank=True
    )
    default_delivery_address = models.TextField(
        blank=True
    )
    emergency_contact_name = models.CharField(
        max_length=100,
        blank=True
    )
    emergency_contact_phone = models.CharField(
        max_length=20,
        blank=True
    )
    preferred_payment_method = models.CharField(
        max_length=30,
        blank=True
    )
    