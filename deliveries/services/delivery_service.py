from decimal import Decimal

from django.db import transaction
from django.utils import timezone

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
        package_fee             -> weight_price
        surge_fee               -> surge_price
        insurance_fee           -> insurance_fee
        service_fee             -> service_fee
        discount                -> discount

    The vehicle multiplier is applied per-component inside
    the pricing calculator, so `base_price`, `distance_price`,
    and `package_fee` are already scaled when they reach this
    service. Delivery.total_price is reconstructed from the
    sum of the mapped fields so that Delivery.clean()'s
    total-price invariant holds.
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
            raise ValueError(
                "An order fulfillment is required."
            )

        # --------------------------------------------------
        # Lock fulfillment
        # --------------------------------------------------

        fulfillment = (
            fulfillment.__class__.objects
            .select_for_update()
            .select_related(
                "order",
                "order__customer",
                "store",
                "store__vendor",
            )
            .get(pk=fulfillment.pk)
        )

        # --------------------------------------------------
        # Validate fulfillment state
        # --------------------------------------------------

        terminal_statuses = {
            fulfillment.Status.CANCELLED,
            fulfillment.Status.FAILED,
            fulfillment.Status.DELIVERED,
        }

        if fulfillment.status in terminal_statuses:

            raise ValueError(
                "A delivery cannot be created for a "
                f"{fulfillment.status} fulfillment."
            )

        # --------------------------------------------------
        # Prevent duplicate delivery
        # --------------------------------------------------

        if hasattr(fulfillment, "delivery"):

            raise ValueError(
                "This fulfillment already has a delivery."
            )

        # --------------------------------------------------
        # Copy validated_data so we do not mutate the
        # caller's dict.
        # --------------------------------------------------

        data = dict(validated_data)

        destination_data = data.pop(
            "destination",
            None,
        )

        if not destination_data:

            raise ValueError(
                "Destination address is required."
            )

        package_size = data.get("package_size")

        if not package_size:

            raise ValueError(
                "Package size is required."
            )

        insurance = bool(
            data.pop("insurance", False)
        )

        declared_value = Decimal(
            str(
                data.pop(
                    "declared_value",
                    Decimal("0.00"),
                )
            )
        )

        # --------------------------------------------------
        # Store / vendor / customer
        # --------------------------------------------------

        store = fulfillment.store
        vendor = store.vendor
        customer = fulfillment.order.customer

        # --------------------------------------------------
        # Store snapshot
        # --------------------------------------------------

        store_snapshot = (
            DeliveryService._get_store_snapshot(
                fulfillment=fulfillment,
            )
        )

        # --------------------------------------------------
        # Package summary
        # --------------------------------------------------

        package_summary = (
            DeliveryService._get_package_summary(
                fulfillment=fulfillment,
            )
        )

        # --------------------------------------------------
        # Create Delivery
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

        pickup_data = (
            DeliveryService._build_pickup_address(
                fulfillment=fulfillment,
                store_snapshot=store_snapshot,
            )
        )

        DeliveryService._require_address_contacts(
            address=pickup_data,
            label="pickup",
        )

        DeliveryAddress.objects.create(
            delivery=delivery,
            address_type=DeliveryAddress.AddressType.PICKUP,
            **pickup_data,
        )

        # --------------------------------------------------
        # Destination address
        # --------------------------------------------------

        DeliveryService._require_address_contacts(
            address=destination_data,
            label="destination",
        )

        DeliveryAddress.objects.create(
            delivery=delivery,
            address_type=(
                DeliveryAddress.AddressType.DELIVERY
            ),
            **destination_data,
        )

        # --------------------------------------------------
        # Route
        # --------------------------------------------------

        route = PricingService.get_route(
            {
                "pickup_latitude": (
                    pickup_data["latitude"]
                ),
                "pickup_longitude": (
                    pickup_data["longitude"]
                ),
                "destination_latitude": (
                    destination_data["latitude"]
                ),
                "destination_longitude": (
                    destination_data["longitude"]
                ),
            }
        )

        delivery.distance_km = route["distance"]
        delivery.estimated_duration_minutes = int(
            Decimal(route["duration"]).quantize(
                Decimal("1"),
            )
        )

        # --------------------------------------------------
        # Price
        # --------------------------------------------------

        pricing_data = {
            "pickup_latitude": pickup_data["latitude"],
            "pickup_longitude": pickup_data["longitude"],
            "destination_latitude": (
                destination_data["latitude"]
            ),
            "destination_longitude": (
                destination_data["longitude"]
            ),
            "package_size": package_size,
            "vehicle_type": delivery.vehicle_type,
            "insurance": insurance,
            "declared_value": declared_value,
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

        if fulfillment.status in {
            fulfillment.Status.PENDING,
            fulfillment.Status.PROCESSING,
            fulfillment.Status.PACKING,
        }:

            fulfillment.status = (
                fulfillment.Status.READY_FOR_DISPATCH
            )
            fulfillment.ready_for_dispatch_at = (
                timezone.now()
            )

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

        def pick(snapshot_field, store_field, default=""):

            value = getattr(
                fulfillment,
                snapshot_field,
                None,
            )

            if value:
                return value

            return getattr(store, store_field, default)

        return {
            "name": pick(
                "store_name",
                "name",
            ),
            "contact_name": (
                getattr(
                    fulfillment,
                    "store_contact_name",
                    "",
                )
                or pick("store_name", "name")
            ),
            "contact_phone": (
                getattr(
                    fulfillment,
                    "store_contact_phone",
                    "",
                )
                or getattr(store, "phone", "")
            ),
            "address_line_1": pick(
                "store_address_line_1",
                "address_line_1",
            ),
            "address_line_2": pick(
                "store_address_line_2",
                "address_line_2",
            ),
            "city": pick(
                "store_city",
                "city",
            ),
            "state": pick(
                "store_state",
                "state",
            ),
            "country": pick(
                "store_country",
                "country",
                "Nigeria",
            ),
            "postal_code": pick(
                "store_postal_code",
                "postal_code",
            ),
            "latitude": fulfillment.store_latitude,
            "longitude": fulfillment.store_longitude,
        }

    # ==================================================
    # Pickup Address
    # ==================================================

    @staticmethod
    def _build_pickup_address(
        fulfillment,
        store_snapshot,
    ):

        return {
            "contact_name": store_snapshot["contact_name"],
            "contact_phone": store_snapshot["contact_phone"],
            "address_line_1": (
                store_snapshot["address_line_1"]
            ),
            "address_line_2": (
                store_snapshot["address_line_2"]
            ),
            "city": store_snapshot["city"],
            "state": store_snapshot["state"],
            "country": store_snapshot["country"],
            "postal_code": store_snapshot["postal_code"],
            "latitude": store_snapshot["latitude"],
            "longitude": store_snapshot["longitude"],
        }

    # ==================================================
    # Address Contact Validation
    # ==================================================

    @staticmethod
    def _require_address_contacts(
        *,
        address,
        label,
    ):

        for field in ("contact_name", "contact_phone"):

            value = address.get(field)

            if not (value or "").strip():

                raise ValueError(
                    f"{label.capitalize()} address is "
                    f"missing {field}."
                )

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
            "weight": total_weight.quantize(
                Decimal("0.001"),
            ),
        }

    # ==================================================
    # Apply Pricing
    # ==================================================

    @staticmethod
    def _apply_pricing(delivery, pricing):
        """
        Map the pricing breakdown onto Delivery fields.

        Assumes the pricing calculator has already applied
        the vehicle multiplier to each per-vehicle
        component, so `base_price`, `distance_price`, and
        `package_fee` are the already-scaled values that
        should be stored directly.
        """

        def q(value):

            return Decimal(str(value)).quantize(
                Decimal("0.01"),
            )

        delivery.base_price = q(
            pricing.get("base_price", 0),
        )
        delivery.distance_price = q(
            pricing.get("distance_price", 0),
        )
        delivery.weight_price = q(
            pricing.get("package_fee", 0),
        )
        delivery.surge_price = q(
            pricing.get("surge_fee", 0),
        )
        delivery.insurance_fee = q(
            pricing.get("insurance_fee", 0),
        )
        delivery.service_fee = q(
            pricing.get("service_fee", 0),
        )
        delivery.discount = q(
            pricing.get("discount", 0),
        )

        # Recompute total from the mapped fields so the
        # Delivery.clean() invariant holds.
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

        delivery.total_price = q(calculated_total)
        delivery.estimated_price = delivery.total_price

        currency = pricing.get("currency")

        if currency:
            delivery.currency = currency