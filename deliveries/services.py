from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from order.models.package import Package
from .models import (
    Delivery,
    DeliveryAddress,
)
from services.pricing_service import PricingService
from deliveries.dispatch.coordinator import (
    DispatchCoordinator,
)


class DeliveryService:
    """
    Service responsible for creating and preparing
    deliveries from OrderFulfillment objects.
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

        The fulfillment is the authoritative source for:

            - customer
            - vendor
            - pickup store
            - store snapshot
            - package information

        validated_data contains delivery-specific data,
        such as:

            {
                "delivery_type": ...,
                "vehicle_type": ...,
                "scheduled_at": ...,
                "notes": ...,
            }

        Address information is expected as:

            {
                "destination": {
                    ...
                }
            }
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
                "store",
                "store__vendor",
            )
            .get(
                pk=fulfillment.pk
            )
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

        if hasattr(
            fulfillment,
            "delivery",
        ):

            raise ValueError(
                "This fulfillment already has a delivery."
            )

        # --------------------------------------------------
        # Extract delivery data
        # --------------------------------------------------

        data = dict(
            validated_data
        )

        destination_data = data.pop(
            "destination",
            None,
        )

        if destination_data is None:

            raise ValueError(
                "Destination address is required."
            )

        # --------------------------------------------------
        # Store
        # --------------------------------------------------

        store = fulfillment.store

        vendor = store.vendor

        # --------------------------------------------------
        # Customer
        # --------------------------------------------------

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
        # Delivery
        # --------------------------------------------------

        delivery = Delivery.objects.create(
            fulfillment=fulfillment,

            customer=customer,

            vendor=vendor,

            pickup_store=store,

            pickup_store_name=(
                store_snapshot["name"]
            ),

            total_package_weight=(
                package_summary["weight"]
            ),

            package_count=(
                package_summary["count"]
            ),

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

        DeliveryAddress.objects.create(
            delivery=delivery,

            address_type=(
                DeliveryAddress.AddressType.PICKUP
            ),

            **pickup_data,
        )

        # --------------------------------------------------
        # Destination address
        # --------------------------------------------------

        DeliveryAddress.objects.create(
            delivery=delivery,

            address_type=(
                DeliveryAddress.AddressType.DELIVERY
            ),

            **destination_data,
        )

        # --------------------------------------------------
        # Calculate route
        # --------------------------------------------------

        route = PricingService._get_route(
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

        delivery.distance_km = (
            route["distance"]
        )

        delivery.estimated_duration_minutes = (
            int(
                route["duration"]
                .quantize(
                    Decimal("1")
                )
            )
        )

        # --------------------------------------------------
        # Calculate price
        # --------------------------------------------------

        pricing_data = {
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

            "package_size": (
                package_summary["weight"]
            ),

            "vehicle_type": (
                delivery.vehicle_type
            ),

            "insurance": (
                data.get(
                    "insurance",
                    False,
                )
            ),

            "declared_value": (
                data.get(
                    "declared_value",
                    Decimal("0.00"),
                )
            ),
        }

        pricing = PricingService.estimate(
            data=pricing_data,
            customer=customer,
        )

        # --------------------------------------------------
        # Save pricing
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

        DispatchCoordinator.delivery_created(
            delivery
        )

        return delivery

    # ==================================================
    # Store Snapshot
    # ==================================================

    @staticmethod
    def _get_store_snapshot(
        fulfillment,
    ):
        """
        Build the pickup-store snapshot.

        The exact field names here should correspond to
        VendorStore.
        """

        store = fulfillment.store

        return {
            "name": (
                getattr(
                    fulfillment,
                    "store_name",
                    None,
                )
                or getattr(
                    store,
                    "name",
                    "",
                )
            ),

            "address_line_1": (
                getattr(
                    fulfillment,
                    "store_address_line_1",
                    None,
                )
                or getattr(
                    store,
                    "address_line_1",
                    "",
                )
            ),

            "address_line_2": (
                getattr(
                    fulfillment,
                    "store_address_line_2",
                    None,
                )
                or getattr(
                    store,
                    "address_line_2",
                    "",
                )
            ),

            "city": (
                getattr(
                    fulfillment,
                    "store_city",
                    None,
                )
                or getattr(
                    store,
                    "city",
                    "",
                )
            ),

            "state": (
                getattr(
                    fulfillment,
                    "store_state",
                    None,
                )
                or getattr(
                    store,
                    "state",
                    "",
                )
            ),

            "country": (
                getattr(
                    fulfillment,
                    "store_country",
                    None,
                )
                or getattr(
                    store,
                    "country",
                    "Nigeria",
                )
            ),

            "postal_code": (
                getattr(
                    fulfillment,
                    "store_postal_code",
                    None,
                )
                or getattr(
                    store,
                    "postal_code",
                    "",
                )
            ),

            "latitude": (
                fulfillment.store_latitude
            ),

            "longitude": (
                fulfillment.store_longitude
            ),
        }

    # ==================================================
    # Pickup Address
    # ==================================================

    @staticmethod
    def _build_pickup_address(
        fulfillment,
        store_snapshot,
    ):
        """
        Convert the fulfillment's store snapshot into
        DeliveryAddress data.
        """

        return {
            "address_line_1": (
                store_snapshot[
                    "address_line_1"
                ]
            ),

            "address_line_2": (
                store_snapshot[
                    "address_line_2"
                ]
            ),

            "city": (
                store_snapshot[
                    "city"
                ]
            ),

            "state": (
                store_snapshot[
                    "state"
                ]
            ),

            "country": (
                store_snapshot[
                    "country"
                ]
            ),

            "postal_code": (
                store_snapshot[
                    "postal_code"
                ]
            ),

            "latitude": (
                store_snapshot[
                    "latitude"
                ]
            ),

            "longitude": (
                store_snapshot[
                    "longitude"
                ]
            ),
        }

    # ==================================================
    # Package Summary
    # ==================================================

    @staticmethod
    def _get_package_summary(
        fulfillment,
    ):
        """
        Calculate package count and total package weight
        from the fulfillment packages.

        Package weight is expected to be stored in
        kilograms.
        """

        packages = fulfillment.packages.all()

        package_count = packages.count()

        total_weight = Decimal(
            "0.000"
        )

        for package in packages:

            weight = getattr(
                package,
                "weight",
                None,
            )

            if weight is None:

                continue

            total_weight += Decimal(
                str(weight)
            )

        return {
            "count": package_count,

            "weight": total_weight.quantize(
                Decimal("0.001")
            ),
        }

    # ==================================================
    # Apply Pricing
    # ==================================================

    @staticmethod
    def _apply_pricing(
        delivery,
        pricing,
    ):
        """
        Map PricingCalculator's result onto Delivery.

        Supports the pricing keys used by the current
        delivery model.
        """

        delivery.base_price = Decimal(
            str(
                pricing.get(
                    "base_price",
                    0,
                )
            )
        )

        delivery.distance_price = Decimal(
            str(
                pricing.get(
                    "distance_price",
                    0,
                )
            )
        )

        delivery.weight_price = Decimal(
            str(
                pricing.get(
                    "weight_price",
                    0,
                )
            )
        )

        delivery.surge_price = Decimal(
            str(
                pricing.get(
                    "surge_price",
                    0,
                )
            )
        )

        delivery.discount = Decimal(
            str(
                pricing.get(
                    "discount",
                    0,
                )
            )
        )

        delivery.insurance_fee = Decimal(
            str(
                pricing.get(
                    "insurance_fee",
                    0,
                )
            )
        )

        delivery.service_fee = Decimal(
            str(
                pricing.get(
                    "service_fee",
                    0,
                )
            )
        )

        delivery.total_price = Decimal(
            str(
                pricing.get(
                    "total_price",
                    0,
                )
            )
        )

        delivery.estimated_price = (
            delivery.total_price
        )

        delivery.currency = pricing.get(
            "currency",
            delivery.currency,
        )