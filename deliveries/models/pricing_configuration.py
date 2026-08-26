from django.utils import timezone
import uuid
from django.conf import settings
from django.db import models
from common.models import TimeStampedModel
from decimal import Decimal
from riders.models import RiderProfile
import uuid



class PricingConfiguration(TimeStampedModel):

    class VehicleType(models.TextChoices):
        BIKE = "BIKE", "Bike"
        CAR = "CAR", "Car"
        VAN = "VAN", "Van"
        TRUCK = "TRUCK", "Truck"

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Example: Lagos Default Pricing",
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # -----------------------
    # Base Pricing
    # -----------------------

    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1000,
    )

    price_per_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=250,
    )

    service_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=300,
    )

    insurance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0100"),  # 1%
        help_text="Decimal percentage (0.01 = 1%)",
    )

    # -----------------------
    # Package Pricing
    # -----------------------

    small_package_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    medium_package_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=300,
    )

    large_package_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=700,
    )

    # -----------------------
    # Vehicle Multipliers
    # -----------------------

    bike_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
    )

    car_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.35,
    )

    van_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.80,
    )

    truck_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.50,
    )

    # -----------------------
    # Surge
    # -----------------------

    enable_surge = models.BooleanField(
        default=False,
    )

    surge_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.50,
    )

    # -----------------------
    # Status
    # -----------------------

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name