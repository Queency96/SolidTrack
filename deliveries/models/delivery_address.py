from django.db import models
from common.models import TimeStampedModel
from deliveries.models.delivery import Delivery




class DeliveryAddress(TimeStampedModel):
    class AddressType(models.TextChoices):
        PICKUP = "PICKUP", "Pickup"
        DELIVERY = "DELIVERY", "Delivery"

    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="addresses",
    )

    address_type = models.CharField(
        max_length=20,
        choices=AddressType.choices,
    )

    contact_name = models.CharField(max_length=255)

    contact_phone = models.CharField(max_length=20)

    address = models.TextField()

    city = models.CharField(max_length=100)

    state = models.CharField(max_length=100)

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    landmark = models.CharField(
        max_length=255,
        blank=True,
    )

    def __str__(self):
        return f"{self.address_type} - {self.address}"


class Package(TimeStampedModel):
    class PackageSize(models.TextChoices):
        SMALL = "SMALL", "Small"
        MEDIUM = "MEDIUM", "Medium"
        LARGE = "LARGE", "Large"

    class PackageCategory(models.TextChoices):
        DOCUMENT = "DOCUMENT", "Document"
        FOOD = "FOOD", "Food"
        ELECTRONICS = "ELECTRONICS", "Electronics"
        CLOTHING = "CLOTHING", "Clothing"
        MEDICAL = "MEDICAL", "Medical"
        OTHER = "OTHER", "Other"

    delivery = models.OneToOneField(
        Delivery,
        on_delete=models.CASCADE,
        related_name="package",
    )

    package_name = models.CharField(
        max_length=255,
    )

    package_category = models.CharField(
        max_length=30,
        choices=PackageCategory.choices,
    )

    package_size = models.CharField(
        max_length=20,
        choices=PackageSize.choices,
    )

    weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    fragile = models.BooleanField(
        default=False,
    )

    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    photo = models.ImageField(
        upload_to="packages/",
        blank=True,
        null=True,
    )

    description = models.TextField(blank=True)

    def __str__(self):
        return self.package_name