from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from order.models.package import Package
from ..models import (
    Delivery,
    DeliveryAddress,
)
from .pricing_service import PricingService
from deliveries.dispatch.coordinator import DispatchCoordinator


class DeliveryService:
    """
    Service responsible for creating and preparing
    deliveries from OrderFulfillment objects.

    Pricing contract
    ----------------
    PricingService.estimate() returns a breakdown whose
    components are mapped onto Delivery fields as follows:

        base_price              -> base_price
        distance_price          -> distance_price
        package_fee * vehicle_multiplier
                                -> weight_price
        surge_fee               -> surge_price
        insurance_fee           -> insurance_fee
        service_fee             -> service_fee
        discount                -> discount

    Delivery.total_price is then recomputed from the sum of
    the mapped components so that Delivery.clean()'s
    total-price invariant holds.

    Delivery has no separate `package_fee` or
    `vehicle_multiplier` column. The calculator's
    `package_fee * vehicle_multiplier` is folded into
    weight_price, which is the pricing slot not otherwise
    used by the calculator.
    """

    # ==================================================
    # Create Delivery
    # ==================================================

    @staticmethod
    @transaction.atomic
    def create_delivery(
        fulfillment,
        validated_data,
    ):
        """
        Create a Delivery for an OrderFulfillment.

        The fulfillment is the authoritative source for
        customer, vendor, pickup store, and package data.

        `validated_data` must include:
            - delivery_type
            - package_size
            - destination (dict)
            - optional: vehicle_type, scheduled_at, notes,
                        insurance, declared_value
        """

        if fulfillment is None:
            raise ValueError("An order fulfillment is required.")

        # --------------------------------------------------
        # Lock fulfillment
        # --------------------------------------------------

        fulfillment = (
            fulfillment.__class__.objects
            .select_for_update()
            .select_related("order", "store", "store__vendor")
            .get(pk=fulfillment.pk)
        )

        # --------------------------------------------------
        # Validate fulfillment state
        # --------------------------------------------------

        if fulfillment.status in [
            fulfillment.Status.CANCELLED,
            fulfillment.Status.FAILED,
            fulfillment.Status.DELIVERED,
        ]:
            raise ValueError(
                "A delivery cannot be created for a "
                f"{fulfillment.status} fulfillment."
            )

        # --------------------------------------------------
        # Prevent duplicate delivery
        # --------------------------------------------------

        if hasattr(fulfillment, "delivery"):
            raise ValueError("This fulfillment already has a delivery.")

        # --------------------------------------------------
        # Extract delivery data
        # --------------------------------------------------

        data = dict(validated_data)

        destination_data = data.pop("destination", None)
        if destination_data is None:
            raise ValueError("Destination address is required.")

        package_size = data.get("package_size")
        if package_size is None:
            raise ValueError("Package size is required.")

        # --------------------------------------------------
        # Store / vendor / customer
        # --------------------------------------------------

        store = fulfillment.store
        vendor = store.vendor
        customer = fulfillment.order.customer

        # --------------------------------------------------
        # Store snapshot
        # --------------------------------------------------

        store_snapshot = DeliveryService._get_store_snapshot(
            fulfillment=fulfillment,
        )

        # --------------------------------------------------
        # Package summary
        # --------------------------------------------------

        package_summary = DeliveryService._get_package_summary(
            fulfillment=fulfillment,
        )

        # --------------------------------------------------
        # Delivery
        # --------------------------------------------------

        delivery = Delivery.objects.create(
            fulfillment=fulfillment,
            customer=customer,
            vendor=vendor,
            pickup_store=store,
            pickup_store_name=store_snapshot["name"],
            package_size=package_size,
            total_package_weight=package_summary["weight"],
            package_count=package_summary["count"],
            **data,
        )

        # --------------------------------------------------
        # Pickup address
        # --------------------------------------------------

        pickup_data = DeliveryService._build_pickup_address(
            fulfillment=fulfillment,
            store_snapshot=store_snapshot,
        )

        DeliveryAddress.objects.create(
            delivery=delivery,
            address_type=DeliveryAddress.AddressType.PICKUP,
            **pickup_data,
        )

        # --------------------------------------------------
        # Destination address
        # --------------------------------------------------

        DeliveryAddress.objects.create(
            delivery=delivery,
            address_type=DeliveryAddress.AddressType.DELIVERY,
            **destination_data,
        )

        # --------------------------------------------------
        # Route
        # --------------------------------------------------

        route = PricingService._get_route(
            {
                "pickup_latitude": pickup_data["latitude"],
                "pickup_longitude": pickup_data["longitude"],
                "destination_latitude": destination_data["latitude"],
                "destination_longitude": destination_data["longitude"],
            }
        )

        delivery.distance_km = route["distance"]
        delivery.estimated_duration_minutes = int(
            route["duration"].quantize(Decimal("1"))
        )

        # --------------------------------------------------
        # Price
        # --------------------------------------------------

        pricing_data = {
            "pickup_latitude": pickup_data["latitude"],
            "pickup_longitude": pickup_data["longitude"],
            "destination_latitude": destination_data["latitude"],
            "destination_longitude": destination_data["longitude"],
            "package_size": package_size,
            "vehicle_type": delivery.vehicle_type,
            "insurance": data.get("insurance", False),
            "declared_value": data.get("declared_value", Decimal("0.00")),
        }

        pricing = PricingService.estimate(
            data=pricing_data,
            customer=customer,
        )

        # --------------------------------------------------
        # Map pricing onto Delivery
        # --------------------------------------------------

        DeliveryService._apply_pricing(
            delivery=delivery,
            pricing=pricing,
        )

        # --------------------------------------------------
        # Final save
        # --------------------------------------------------

        delivery.save()

        # --------------------------------------------------
        # Update fulfillment
        # --------------------------------------------------

        if fulfillment.status in [
            fulfillment.Status.PENDING,
            fulfillment.Status.PROCESSING,
            fulfillment.Status.PACKING,
        ]:
            fulfillment.status = fulfillment.Status.READY_FOR_DISPATCH
            fulfillment.ready_for_dispatch_at = timezone.now()
            fulfillment.save(
                update_fields=[
                    "status",
                    "ready_for_dispatch_at",
                    "updated_at",
                ]
            )

        # --------------------------------------------------
        # Start dispatch workflow
        # --------------------------------------------------

        DispatchCoordinator.delivery_created(delivery)

        return delivery

    # ==================================================
    # Store Snapshot
    # ==================================================

    @staticmethod
    def _get_store_snapshot(fulfillment):
        store = fulfillment.store

        return {
            "name": (
                getattr(fulfillment, "store_name", None)
                or getattr(store, "name", "")
            ),
            "address_line_1": (
                getattr(fulfillment, "store_address_line_1", None)
                or getattr(store, "address_line_1", "")
            ),
            "address_line_2": (
                getattr(fulfillment, "store_address_line_2", None)
                or getattr(store, "address_line_2", "")
            ),
            "city": (
                getattr(fulfillment, "store_city", None)
                or getattr(store, "city", "")
            ),
            "state": (
                getattr(fulfillment, "store_state", None)
                or getattr(store, "state", "")
            ),
            "country": (
                getattr(fulfillment, "store_country", None)
                or getattr(store, "country", "Nigeria")
            ),
            "postal_code": (
                getattr(fulfillment, "store_postal_code", None)
                or getattr(store, "postal_code", "")
            ),
            "latitude": fulfillment.store_latitude,
            "longitude": fulfillment.store_longitude,
        }

    # ==================================================
    # Pickup Address
    # ==================================================

    @staticmethod
    def _build_pickup_address(fulfillment, store_snapshot):
        return {
            "address_line_1": store_snapshot["address_line_1"],
            "address_line_2": store_snapshot["address_line_2"],
            "city": store_snapshot["city"],
            "state": store_snapshot["state"],
            "country": store_snapshot["country"],
            "postal_code": store_snapshot["postal_code"],
            "latitude": store_snapshot["latitude"],
            "longitude": store_snapshot["longitude"],
        }

    # ==================================================
    # Package Summary
    # ==================================================

    @staticmethod
    def _get_package_summary(fulfillment):
        packages = fulfillment.packages.all()

        package_count = packages.count()
        total_weight = Decimal("0.000")

        for package in packages:
            weight = getattr(package, "weight", None)
            if weight is None:
                continue
            total_weight += Decimal(str(weight))

        return {
            "count": package_count,
            "weight": total_weight.quantize(Decimal("0.001")),
        }

    # ==================================================
    # Apply Pricing
    # ==================================================

    @staticmethod
    def _apply_pricing(delivery, pricing):
        """
        Map PricingCalculator's result onto Delivery.

        See module docstring for the mapping and rationale.
        """

        delivery.base_price = Decimal(
            str(pricing.get("base_price", 0))
        ).quantize(Decimal("0.01"))

        delivery.distance_price = Decimal(
            str(pricing.get("distance_price", 0))
        ).quantize(Decimal("0.01"))

        # package_fee * vehicle_multiplier -> weight_price
        package_fee = Decimal(
            str(pricing.get("package_fee", 0))
        )
        vehicle_multiplier = Decimal(
            str(pricing.get("vehicle_multiplier", 1))
        )
        delivery.weight_price = (
            package_fee * vehicle_multiplier
        ).quantize(Decimal("0.01"))

        delivery.surge_price = Decimal(
            str(pricing.get("surge_fee", 0))
        ).quantize(Decimal("0.01"))

        delivery.insurance_fee = Decimal(
            str(pricing.get("insurance_fee", 0))
        ).quantize(Decimal("0.01"))

        delivery.service_fee = Decimal(
            str(pricing.get("service_fee", 0))
        ).quantize(Decimal("0.01"))

        delivery.discount = Decimal(
            str(pricing.get("discount", 0))
        ).quantize(Decimal("0.01"))

        # Recompute total from mapped components so that
        # Delivery.clean()'s invariant holds.
        calculated_total = (
            delivery.base_price
            + delivery.distance_price
            + delivery.weight_price
            + delivery.surge_price
            + delivery.insurance_fee
            + delivery.service_fee
            - delivery.discount
        )

        if calculated_total < Decimal("0.00"):
            calculated_total = Decimal("0.00")

        delivery.total_price = calculated_total.quantize(Decimal("0.01"))

        delivery.estimated_price = delivery.total_price
        delivery.currency = pricing.get("currency", delivery.currency)