from decimal import Decimal

from django.db import transaction

from order.models import (
    Package,
    PackageItem,
)


class PackageService:
    """
    Service responsible for creating physical packages
    for an OrderFulfillment.

    A package groups one or more OrderItems (with
    quantities) so the vendor can pack, weigh, and hand
    them to a rider as a single unit.

    Weight is computed from OrderItem.unit_weight, which
    is snapshotted at checkout. Items whose unit weight
    is unknown contribute nothing to the total.
    """

    # ==================================================
    # Create Packages for Fulfillment
    # ==================================================

    @classmethod
    @transaction.atomic
    def create_for_fulfillment(
        cls,
        *,
        fulfillment,
    ):
        """
        Create the initial physical package for an order
        fulfillment.

        The initial implementation creates one package
        containing all fulfillable items. Items marked
        UNAVAILABLE are excluded.

        Raises ValueError when the fulfillment has no
        fulfillable items or already has packages.
        """

        if fulfillment is None:
            raise ValueError(
                "Fulfillment is required."
            )

        # --------------------------------------------------
        # Lock the fulfillment so concurrent calls cannot
        # both create packages.
        # --------------------------------------------------

        fulfillment = (
            fulfillment.__class__.objects
            .select_for_update()
            .get(pk=fulfillment.pk)
        )

        # --------------------------------------------------
        # Prevent duplicate package creation.
        # --------------------------------------------------

        if fulfillment.packages.exists():

            raise ValueError(
                "Packages have already been created "
                "for this fulfillment."
            )

        # --------------------------------------------------
        # Load fulfillable items.
        # --------------------------------------------------

        items = list(
            fulfillment.items
            .select_related(
                "product",
                "variant",
            )
            .exclude(
                fulfillment_status=(
                    fulfillment.items.model
                    .FulfillmentStatus
                    .UNAVAILABLE
                ),
            )
        )

        if not items:

            raise ValueError(
                "Cannot create a package for a "
                "fulfillment without fulfillable "
                "order items."
            )

        # --------------------------------------------------
        # Aggregate weight and declared value.
        #
        # Weight comes from the historical snapshot on
        # OrderItem, never from the live catalog.
        # --------------------------------------------------

        total_weight = Decimal("0.000")
        declared_value = Decimal("0.00")

        for item in items:

            if item.unit_weight is not None:

                total_weight += (
                    item.unit_weight
                    * Decimal(item.quantity)
                )

            declared_value += (
                Decimal(str(item.subtotal))
            )

        total_weight = total_weight.quantize(
            Decimal("0.001"),
        )

        declared_value = declared_value.quantize(
            Decimal("0.01"),
        )

        # --------------------------------------------------
        # Create the package.
        # --------------------------------------------------

        package = Package.objects.create(
            fulfillment=fulfillment,
            package_type=Package.PackageType.CUSTOM,
            status=Package.Status.CREATED,
            weight=total_weight,
            declared_value=declared_value,
            currency=fulfillment.currency or "NGN",
        )

        # --------------------------------------------------
        # Create the package items.
        # --------------------------------------------------

        PackageItem.objects.bulk_create(
            [
                PackageItem(
                    package=package,
                    order_item=item,
                    quantity=item.quantity,
                )
                for item in items
            ]
        )

        return package