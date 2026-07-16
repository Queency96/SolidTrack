from django.db import models
from django.conf import settings
from common.models import TimeStampedModel
import uuid



class VendorProfile(TimeStampedModel):
    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vendor_profile"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_vendors",
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    rejection_reason = models.TextField(
        blank=True,
    )
    company_name = models.CharField(max_length=255)
    business_registration_number = models.CharField(
        max_length=100,
        blank=True
    )
    tax_number = models.CharField(
        max_length=100,
        blank=True
    )
    company_logo = models.ImageField(
        upload_to="vendors/",
        blank=True,
        null=True
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    def __str__(self):
        return self.company_name