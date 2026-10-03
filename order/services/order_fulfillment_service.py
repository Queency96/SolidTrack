from decimal import Decimal
import uuid

from django.db import transaction
from django.utils import timezone

from deliveries.models import (
    Delivery,
    DeliveryAddress,
)
from deliveries.dispatch.assignment import AssignmentService
from deliveries.services.delivery_service import DeliveryService
from deliveries.services.pricing_service import PricingService

from ..models import (
    Order,
    OrderFulfillment,
    Package,
)


class OrderFulfillmentService:
    """
    Coordinates the lifecycle of an OrderFulfillment.

    Delivery creation is delegated to
    DeliveryService.create_delivery (O3-B). This service
    does not duplicate route, pricing, or dispatch logic.
    """

    # ==================================================
    # Start Processing
    # ==================================================

    @classmethod
    @transaction.atomic
    def start_processing(cls, *, fulfillment):
        fulfillment = cls._lock_fulfillment(fulfillment=fulfillment)
        cls._ensure_not_terminal(fulfillment=fulfillment)

        if fulfillment.status != OrderFulfillment.Status.PENDING:
            raise ValueError("Fulfillment is not pending.")

        cls._ensure_order_can_fulfill(fulfillment=fulfillment)

        fulfillment.status = OrderFulfillment.Status.PROCESSING
        fulfillment.processing_at = timezone.now()

        fulfillment.save(update_fields=["status", "processing_at", "updated_at"])
        return fulfillment

    # ==================================================
    # Start Packing
    # ==================================================

    @classmethod
    @transaction.atomic
    def start_packing(cls, *, fulfillment):
        fulfillment = cls._lock_fulfillment(fulfillment=fulfillment)
        cls._ensure_not_terminal(fulfillment=fulfillment)

        if fulfillment.status != OrderFulfillment.Status.PROCESSING:
            raise ValueError(
                "Fulfillment must be processing before packing can begin."
            )

        cls._ensure_order_can_fulfill(fulfillment=fulfillment)

        fulfillment.status = OrderFulfillment.Status.PACKING
        fulfillment.packing_at = timezone.now()

        fulfillment.save(update_fields=["status", "packing_at", "updated_at"])
        return fulfillment

    # ==================================================
    # Create Package
    # ==================================================

    @classmethod
    @transaction.atomic
    def create_package(
        cls,
        *,
        fulfillment,
        package_type=Package.PackageType.CUSTOM,
        weight=Decimal("0.000"),
        length=Decimal("0.00"),
        width=Decimal("0.00"),
        height=Decimal("0.00"),
        declared_value=Decimal("0.00"),
        is_fragile=False,
        requires_special_handling=False,
        special_handling_note="",
        description="",
        packaging_note="",
    ):
        fulfillment = cls._lock_fulfillment(fulfillment=fulfillment)

        if fulfillment.status not in [
            OrderFulfillment.Status.PROCESSING,
            OrderFulfillment.Status.PACKING,
        ]:
            raise ValueError(
                "Packages can only be created while the fulfillment "
                "is being prepared."
            )

        cls._ensure_order_can_fulfill(fulfillment=fulfillment)

        cls._validate_package_values(
            weight=weight, length=length, width=width,
            height=height, declared_value=declared_value,
        )

        return Package.objects.create(
            fulfillment=fulfillment,
            package_number=cls._generate_package_number(),
            tracking_number=cls._generate_package_tracking_number(),
            package_type=package_type,
            status=Package.Status.CREATED,
            weight=weight,
            length=length,
            width=width,
            height=height,
            declared_value=declared_value,
            currency=fulfillment.currency,
            is_fragile=is_fragile,
            requires_special_handling=requires_special_handling,
            special_handling_note=special_handling_note,
            description=description,
            packaging_note=packaging_note,
        )

    # ==================================================
    # Start Package Packing
    # ==================================================

    @classmethod
    @transaction.atomic
    def start_package_packing(cls, *, package):
        package = cls._lock_package(package=package)

        if package.status != Package.Status.CREATED:
            raise ValueError("Package is not in the created state.")

        fulfillment = cls._lock_fulfillment(
            fulfillment=package.fulfillment,
        )

        if fulfillment.status not in [
            OrderFulfillment.Status.PROCESSING,
            OrderFulfillment.Status.PACKING,
        ]:
            raise ValueError(
                "Fulfillment is not currently being prepared."
            )

        package.status = Package.Status.PACKING
        package.save(update_fields=["status", "updated_at"])
        return package

    # ==================================================
    # Mark Package Packed
    # ==================================================

    @classmethod
    @transaction.atomic
    def mark_package_packed(cls, *, package):
        package = cls._lock_package(package=package)

        if package.status not in [
            Package.Status.CREATED,
            Package.Status.PACKING,
        ]:
            raise ValueError(
                "Package cannot be marked as packed from its current state."
            )

        package.status = Package.Status.PACKED
        package.packed_at = timezone.now()
        package.save(update_fields=["status", "packed_at", "updated_at"])
        return package

    # ==================================================
    # Mark Package Ready
    # ==================================================

    @classmethod
    @transaction.atomic
    def mark_package_ready(cls, *, package):
        package = cls._lock_package(package=package)

        if package.status != Package.Status.PACKED:
            raise ValueError(
                "Package must be packed before it can be ready for pickup."
            )

        package.status = Package.Status.READY_FOR_PICKUP
        package.ready_for_pickup_at = timezone.now()
        package.save(
            update_fields=["status", "ready_for_pickup_at", "updated_at"]
        )
        return package

    # ==================================================
    # Mark Fulfillment Ready
    # ==================================================

    @classmethod
    @transaction.atomic
    def mark_ready_for_dispatch(cls, *, fulfillment):
        """
        Mark fulfillment ready for dispatch.

        Delivery creation is delegated to
        DeliveryService.create_delivery (O3-B). This service
        is responsible only for validating fulfillment
        readiness and passing the delivery inputs through.
        """

        fulfillment = cls._lock_fulfillment(fulfillment=fulfillment)
        cls._ensure_not_terminal(fulfillment=fulfillment)

        if fulfillment.status not in [
            OrderFulfillment.Status.PACKING,
            OrderFulfillment.Status.PROCESSING,
        ]:
            raise ValueError(
                "Fulfillment is not currently being prepared."
            )

        cls._ensure_order_can_fulfill(fulfillment=fulfillment)
        cls._validate_fulfillment_items(fulfillment=fulfillment)

        packages = list(fulfillment.packages.all())

        if not packages:
            raise ValueError(
                "Fulfillment must have at least one package before dispatch."
            )

        not_ready = [
            package
            for package in packages
            if package.status != Package.Status.READY_FOR_PICKUP
        ]

        if not_ready:
            raise ValueError(
                "All packages must be ready for pickup before dispatch."
            )

        fulfillment.status = OrderFulfillment.Status.READY_FOR_DISPATCH
        fulfillment.ready_for_dispatch_at = timezone.now()
        fulfillment.save(
            update_fields=[
                "status",
                "ready_for_dispatch_at",
                "updated_at",
            ]
        )

        delivery = cls._create_delivery(fulfillment=fulfillment)
        return fulfillment, delivery

    # ==================================================
    # Create Delivery (delegates to DeliveryService)
    # ==================================================

    @classmethod
    def _create_delivery(cls, *, fulfillment):
        """
        Delegate delivery creation to the canonical
        DeliveryService.create_delivery.

        Idempotent: if a Delivery already exists for this
        fulfillment, it is returned and DeliveryService is
        not called again.
        """

        existing = (
            Delivery.objects
            .select_for_update()
            .filter(fulfillment=fulfillment)
            .first()
        )

        if existing:
            return existing

        destination = cls._build_destination_data(fulfillment=fulfillment)

        validated_data = {
            "delivery_type": fulfillment.delivery_type,
            "package_size": fulfillment.package_size,
            "vehicle_type": fulfillment.vehicle_type,
            "scheduled_at": fulfillment.scheduled_at,
            "notes": fulfillment.preparation_note or "",
            "destination": destination,
        }

        return DeliveryService.create_delivery(
            fulfillment=fulfillment,
            validated_data=validated_data,
        )

    # ==================================================
    # Destination Data
    # ==================================================

    @staticmethod
    def _build_destination_data(*, fulfillment):
        """
        Build the destination dict that DeliveryService
        expects (validated_data["destination"]).

        OrderFulfillment carries the destination snapshot.
        """

        return {
            "address_line_1": fulfillment.delivery_address_line_1,
            "address_line_2": fulfillment.delivery_address_line_2,
            "city": fulfillment.delivery_city,
            "state": fulfillment.delivery_state,
            "country": fulfillment.delivery_country,
            "postal_code": fulfillment.delivery_postal_code,
            "latitude": fulfillment.delivery_latitude,
            "longitude": fulfillment.delivery_longitude,
            "instructions": fulfillment.delivery_instructions or "",
        }

    # ==================================================
    # Dispatch
    # ==================================================

    @classmethod
    @transaction.atomic
    def mark_dispatched(cls, *, fulfillment):
        fulfillment = cls._lock_fulfillment(fulfillment=fulfillment)

        if fulfillment.status != OrderFulfillment.Status.READY_FOR_DISPATCH:
            raise ValueError("Fulfillment is not ready for dispatch.")

        delivery = (
            Delivery.objects
            .select_for_update()
            .filter(fulfillment=fulfillment)
            .first()
        )

        if delivery is None:
            raise ValueError("Fulfillment does not have a delivery.")

        if delivery.status not in [
            Delivery.DeliveryStatus.RIDER_ASSIGNED,
            Delivery.DeliveryStatus.RIDER_ACCEPTED,
        ]:
            raise ValueError(
                "Delivery must have an assigned or accepted rider "
                "before the fulfillment can be dispatched."
            )

        fulfillment.status = OrderFulfillment.Status.DISPATCHED
        fulfillment.dispatched_at = timezone.now()
        fulfillment.save(
            update_fields=["status", "dispatched_at", "updated_at"]
        )
        return fulfillment

    # ==================================================
    # Out For Delivery
    # ==================================================

    @classmethod
    @transaction.atomic
    def mark_out_for_delivery(cls, *, fulfillment):
        fulfillment = cls._lock_fulfillment(fulfillment=fulfillment)

        if fulfillment.status != OrderFulfillment.Status.DISPATCHED:
            raise ValueError(
                "Fulfillment must be dispatched before going out for delivery."
            )

        fulfillment.status = OrderFulfillment.Status.OUT_FOR_DELIVERY
        fulfillment.out_for_delivery_at = timezone.now()
        fulfillment.save(
            update_fields=["status", "out_for_delivery_at", "updated_at"]
        )
        return fulfillment

    # ==================================================
    # Delivered
    # ==================================================

    @classmethod
    @transaction.atomic
    def mark_delivered(cls, *, fulfillment):
        fulfillment = cls._lock_fulfillment(fulfillment=fulfillment)

        if fulfillment.status != OrderFulfillment.Status.OUT_FOR_DELIVERY:
            raise ValueError(
                "Fulfillment must be out for delivery before it can be delivered."
            )

        packages = list(fulfillment.packages.all())

        if not packages:
            raise ValueError("Fulfillment has no packages.")

        not_delivered = [
            package
            for package in packages
            if package.status != Package.Status.DELIVERED
        ]

        if not_delivered:
            raise ValueError(
                "All packages must be delivered before the "
                "fulfillment is marked delivered."
            )

        fulfillment.status = OrderFulfillment.Status.DELIVERED
        fulfillment.delivered_at = timezone.now()
        fulfillment.save(
            update_fields=["status", "delivered_at", "updated_at"]
        )

        cls._update_order_status(fulfillment=fulfillment)
        return fulfillment

    # ==================================================
    # Cancel
    # ==================================================

    @classmethod
    @transaction.atomic
    def cancel(cls, *, fulfillment, cancelled_by=None, reason=""):
        """
        Cancel a fulfillment.

        Delivery cancellation is delegated to
        AssignmentService.cancel_fulfillment (O5-C), which
        owns Delivery.status transitions and rider
        availability restore.
        """

        fulfillment = cls._lock_fulfillment(fulfillment=fulfillment)

        if fulfillment.status in [
            OrderFulfillment.Status.DELIVERED,
            OrderFulfillment.Status.CANCELLED,
        ]:
            raise ValueError(
                "Fulfillment cannot be cancelled from its current state."
            )

        fulfillment.status = OrderFulfillment.Status.CANCELLED
        fulfillment.cancelled_at = timezone.now()
        fulfillment.save(
            update_fields=["status", "cancelled_at", "updated_at"]
        )

        # Delegate delivery/assignment cancellation.
        AssignmentService.cancel_fulfillment(
            fulfillment=fulfillment,
            cancelled_by=cancelled_by,
            reason=reason or "Fulfillment cancelled.",
        )

        return fulfillment

    # ==================================================
    # Validate Items
    # ==================================================

    @staticmethod
    def _validate_fulfillment_items(*, fulfillment):
        if not fulfillment.items.exists():
            raise ValueError(
                "Fulfillment must contain at least one order item."
            )

        invalid_items = (
            fulfillment.items
            .exclude(store_id=fulfillment.store_id)
            .exists()
        )

        if invalid_items:
            raise ValueError(
                "Fulfillment contains an item belonging to another store."
            )

    # ==================================================
    # Validate Package Values
    # ==================================================

    @staticmethod
    def _validate_package_values(
        *, weight, length, width, height, declared_value,
    ):
        values = {
            "weight": weight,
            "length": length,
            "width": width,
            "height": height,
            "declared_value": declared_value,
        }
        for field_name, value in values.items():
            if value is None:
                continue
            if Decimal(str(value)) < Decimal("0"):
                raise ValueError(
                    f"{field_name.replace('_', ' ').capitalize()} cannot be negative."
                )

    # ==================================================
    # Validate Order
    # ==================================================

    @staticmethod
    def _ensure_order_can_fulfill(*, fulfillment):
        order = fulfillment.order

        if order.payment_status != Order.PaymentStatus.PAID:
            raise ValueError(
                "Order must be paid before the fulfillment can be processed."
            )

        if order.status in [Order.Status.CANCELLED, Order.Status.FAILED]:
            raise ValueError("The order cannot be fulfilled.")

    # ==================================================
    # Terminal
    # ==================================================

    @staticmethod
    def _ensure_not_terminal(*, fulfillment):
        if fulfillment.status in [
            OrderFulfillment.Status.DELIVERED,
            OrderFulfillment.Status.CANCELLED,
            OrderFulfillment.Status.FAILED,
        ]:
            raise ValueError("Fulfillment is in a terminal state.")

    # ==================================================
    # Lock Fulfillment
    # ==================================================

    @staticmethod
    def _lock_fulfillment(*, fulfillment):
        return (
            OrderFulfillment.objects
            .select_for_update()
            .select_related("order", "store", "store__vendor")
            .prefetch_related("items", "packages")
            .get(pk=fulfillment.pk)
        )

    # ==================================================
    # Lock Package
    # ==================================================

    @staticmethod
    def _lock_package(*, package):
        return (
            Package.objects
            .select_for_update()
            .select_related("fulfillment", "fulfillment__order")
            .get(pk=package.pk)
        )

    # ==================================================
    # Package Number
    # ==================================================

    @staticmethod
    def _generate_package_number():
        return (
            f"PKG-{timezone.now():%Y%m%d}-"
            f"{uuid.uuid4().hex[:10].upper()}"
        )

    # ==================================================
    # Package Tracking Number
    # ==================================================

    @staticmethod
    def _generate_package_tracking_number():
        return f"PKG-TRK-{uuid.uuid4().hex[:12].upper()}"

    # ==================================================
    # Update Order Status
    # ==================================================

    @classmethod
    def _update_order_status(cls, *, fulfillment):
        order = (
            Order.objects
            .select_for_update()
            .get(pk=fulfillment.order_id)
        )

        fulfillments = list(order.fulfillments.all())

        if not fulfillments:
            return

        active = [
            item
            for item in fulfillments
            if item.status != OrderFulfillment.Status.CANCELLED
        ]

        if not active:
            return

        if all(item.status == OrderFulfillment.Status.DELIVERED for item in active):
            order.status = Order.Status.DELIVERED
            order.delivered_at = timezone.now()
            order.save(update_fields=["status", "delivered_at", "updated_at"])
            return

        if any(item.status == OrderFulfillment.Status.OUT_FOR_DELIVERY for item in active):
            order.status = Order.Status.OUT_FOR_DELIVERY
            order.save(update_fields=["status", "updated_at"])
            return

        if any(item.status == OrderFulfillment.Status.DISPATCHED for item in active):
            order.status = Order.Status.PROCESSING
            order.save(update_fields=["status", "updated_at"])
            return

        if any(item.status == OrderFulfillment.Status.READY_FOR_DISPATCH for item in active):
            order.status = Order.Status.READY_FOR_DISPATCH
            order.save(update_fields=["status", "updated_at"])
            return

        if any(
            item.status in [
                OrderFulfillment.Status.PROCESSING,
                OrderFulfillment.Status.PACKING,
            ]
            for item in active
        ):
            order.status = Order.Status.PROCESSING
            order.save(update_fields=["status", "updated_at"])
            return

        if any(item.status == OrderFulfillment.Status.PENDING for item in active):
            order.status = Order.Status.PENDING
            order.save(update_fields=["status", "updated_at"])
            return