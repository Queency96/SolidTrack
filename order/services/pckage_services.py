from decimal import Decimal
from django.db import transaction
from order.models import Package, PackageItem


class PackageService:

    @classmethod
    @transaction.atomic
    def create_for_fulfillment(
        cls,
        *,
        fulfillment,
    ):
        """
        Create the initial physical package for
        an order fulfillment.

        The initial implementation creates one package
        containing all fulfillment items.
        """

        if fulfillment is None:
            raise ValueError(
                "Fulfillment is required."
            )

        existing = fulfillment.packages.exists()

        if existing:
            raise ValueError(
                "Packages have already been created "
                "for this fulfillment."
            )

        items = list(
            fulfillment.items.all()
        )

        if not items:
            raise ValueError(
                "Cannot create a package for a "
                "fulfillment without order items."
            )

        total_weight = Decimal("0.000")

        package = Package.objects.create(
            fulfillment=fulfillment,
            package_type=Package.PackageType.CUSTOM,
            status=Package.Status.CREATED,
            weight=Decimal("0.000"),
            declared_value=Decimal("0.00"),
            currency="NGN",
        )

        for item in items:

            PackageItem.objects.create(
                package=package,
                order_item=item,
                quantity=item.quantity,
            )

        return package