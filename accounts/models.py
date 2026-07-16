from django.db import models
import uuid
from datetime import timedelta
from django.utils import timezone
import random
from django.contrib.auth.models import AbstractUser
from common.models import TimeStampedModel
from .managers import UserManager
import uuid




class User(AbstractUser, TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    class Roles(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        VENDOR = "VENDOR", "Vendor"
        RIDER = "RIDER", "Rider"
        ADMIN = "ADMIN", "Admin"

    username = None
    first_name = models.CharField(
        max_length=100
    )
    last_name = models.CharField(
        max_length=100
    )
    email = models.EmailField(
        unique=True
    )
    phone_number = models.CharField(
        max_length=20,
        unique=True
    )
    profile_picture = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True
    )
    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.CUSTOMER
    )
    is_email_verified = models.BooleanField(
        default=False
    )
    is_phone_verified = models.BooleanField(
        default=False
    )
    USERNAME_FIELD = "email"
    
    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
        "phone_number",
    ]

    objects = UserManager()

    def __str__(self):
        return self.email



class EmailVerification(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_verifications"
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)

        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.user.email}"


class PhoneOTP(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="phone_otps"
    )
    code = models.CharField(
        max_length=6
    )
    is_used = models.BooleanField(
        default=False
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"{random.randint(100000,999999)}"

        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)

        super().save(*args, **kwargs)

    def is_expired(self):

        return timezone.now() > self.expires_at

    def __str__(self):

        return f"{self.user.phone_number}"



