from decimal import Decimal
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from cloudinary.models import CloudinaryField

from common.constant import (
    NIGERIA_STATE_CHOICES,
    VALID_STATE_CODES,
    normalize_state,
)
from common.models import TimeStampedModel


# ======================================================
# VendorProfile
# ======================================================

class VendorProfile(TimeStampedModel):

    class VerificationStatus(models.TextChoices):
        PENDING = ("PENDING", "Pending")
        APPROVED = ("APPROVED", "Approved")
        REJECTED = ("REJECTED", "Rejected")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vendor_profile",
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
        default="",
    )

    company_name = models.CharField(max_length=255)

    business_registration_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    tax_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    company_logo = models.ImageField(
        upload_to="vendors/",
        blank=True,
        null=True,
    )

    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.company_name

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):

        if not self.company_name.strip():
            raise ValidationError(
                {"company_name": "Company name cannot be empty."}
            )

        if self.verification_status == self.VerificationStatus.APPROVED:
            if self.approved_at is None:
                raise ValidationError(
                    {"approved_at": "Approved vendors require an approval timestamp."}
                )
            if self.approved_by_id is None:
                raise ValidationError(
                    {"approved_by": "Approved vendors require an approver."}
                )

        if self.verification_status == self.VerificationStatus.REJECTED:
            if not self.rejection_reason.strip():
                raise ValidationError(
                    {"rejection_reason": "Rejected vendors require a rejection reason."}
                )

    # ==================================================
    # Save
    # ==================================================

    def save(self, *args, **kwargs):
        if self._state.adding or kwargs.pop("full_clean", False):
            self.full_clean()
        super().save(*args, **kwargs)
