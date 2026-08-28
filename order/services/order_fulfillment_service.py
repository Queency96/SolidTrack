from decimal import Decimal
import uuid

from django.db import transaction
from django.utils import timezone

from ..models import (
    Order,
    OrderFulfillment,
    Package,
    Delivery,
)


class OrderFulfillmentService:
    """
    Coordinates the lifecycle of an OrderFulfillment.

    Fulfillment lifecycle:

        PENDING
           ↓
        PROCESSING
           ↓
        PACKING
           ↓
        READY_FOR_DISPATCH
           ↓
        Delivery Created
           ↓
        DispatchPipeline
           ↓
        DISPATCHED
           ↓
        OUT_FOR_DELIVERY
           ↓
        DELIVERED

    Responsibilities:

        - Start fulfillment
        - Start packing
        - Create packages
        - Validate packages
        - Mark fulfillment ready
        - Create delivery
        - Mark fulfillment dispatched
        - Mark fulfillment out for delivery
        - Mark fulfillment delivered
        - Cancel fulfillment

    Rider matching and assignment are intentionally
    delegated to DispatchPipeline / AssignmentService.
    """

    # ==================================================
    # Start Processing
    # ==================================================

    @classmethod
    @transaction.atomic
    def start_processing(
        cls,
        *,
        fulfillment,
    ):
        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )

        cls._ensure_not_terminal(
            fulfillment=fulfillment,
        )

        if fulfillment.status != (
            OrderFulfillment.Status.PENDING
        ):
            raise ValueError(
                "Fulfillment is not pending."
            )

        cls._ensure_order_can_fulfill(
            fulfillment=fulfillment,
        )

        fulfillment.status = (
            OrderFulfillment.Status.PROCESSING
        )

        fulfillment.processing_at = (
            timezone.now()
        )

        fulfillment.save(
            update_fields=[
                "status",
                "processing_at",
                "updated_at",
            ]
        )

        return fulfillment

    # ==================================================
    # Start Packing
    # ==================================================

    @classmethod
    @transaction.atomic
    def start_packing(
        cls,
        *,
        fulfillment,
    ):
        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )

        cls._ensure_not_terminal(
            fulfillment=fulfillment,
        )

        if fulfillment.status != (
            OrderFulfillment.Status.PROCESSING
        ):
            raise ValueError(
                "Fulfillment must be processing "
                "before packing can begin."
            )

        cls._ensure_order_can_fulfill(
            fulfillment=fulfillment,
        )

        fulfillment.status = (
            OrderFulfillment.Status.PACKING
        )

        fulfillment.packing_at = (
            timezone.now()
        )

        fulfillment.save(
            update_fields=[
                "status",
                "packing_at",
                "updated_at",
            ]
        )

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
        """
        Create a physical package for a fulfillment.
        """

        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )

        if fulfillment.status not in [
            OrderFulfillment.Status.PROCESSING,
            OrderFulfillment.Status.PACKING,
        ]:
            raise ValueError(
                "Packages can only be created while "
                "the fulfillment is being prepared."
            )

        cls._ensure_order_can_fulfill(
            fulfillment=fulfillment,
        )

        package = Package.objects.create(
            fulfillment=fulfillment,

            package_number=(
                cls._generate_package_number()
            ),

            tracking_number=(
                cls._generate_package_tracking_number()
            ),

            package_type=package_type,

            status=Package.Status.CREATED,

            weight=weight,
            length=length,
            width=width,
            height=height,

            declared_value=declared_value,

            currency=fulfillment.currency,

            is_fragile=is_fragile,

            requires_special_handling=(
                requires_special_handling
            ),

            special_handling_note=(
                special_handling_note
            ),

            description=description,

            packaging_note=packaging_note,
        )

        return package

    # ==================================================
    # Start Package Packing
    # ==================================================

    @classmethod
    @transaction.atomic
    def start_package_packing(
        cls,
        *,
        package,
    ):
        package = cls._lock_package(
            package=package,
        )

        if package.status != (
            Package.Status.CREATED
        ):
            raise ValueError(
                "Package is not in the created state."
            )

        fulfillment = cls._lock_fulfillment(
            fulfillment=package.fulfillment,
        )

        if fulfillment.status not in [
            OrderFulfillment.Status.PROCESSING,
            OrderFulfillment.Status.PACKING,
        ]:
            raise ValueError(
                "Fulfillment is not currently "
                "being prepared."
            )

        package.status = (
            Package.Status.PACKING
        )

        package.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return package

    # ==================================================
    # Mark Package Packed
    # ==================================================

    @classmethod
    @transaction.atomic
    def mark_package_packed(
        cls,
        *,
        package,
    ):
        package = cls._lock_package(
            package=package,
        )

        if package.status not in [
            Package.Status.CREATED,
            Package.Status.PACKING,
        ]:
            raise ValueError(
                "Package cannot be marked as packed "
                "from its current state."
            )

        package.status = (
            Package.Status.PACKED
        )

        package.packed_at = (
            timezone.now()
        )

        package.save(
            update_fields=[
                "status",
                "packed_at",
                "updated_at",
            ]
        )

        return package

    # ==================================================
    # Mark Package Ready
    # ==================================================

    @classmethod
    @transaction.atomic
    def mark_package_ready(
        cls,
        *,
        package,
    ):
        package = cls._lock_package(
            package=package,
        )

        if package.status != (
            Package.Status.PACKED
        ):
            raise ValueError(
                "Package must be packed before "
                "it can be ready for pickup."
            )

        package.status = (
            Package.Status.READY_FOR_PICKUP
        )

        package.ready_for_pickup_at = (
            timezone.now()
        )

        package.save(
            update_fields=[
                "status",
                "ready_for_pickup_at",
                "updated_at",
            ]
        )

        return package

    # ==================================================
    # Mark Fulfillment Ready
    # ==================================================

    @classmethod
    @transaction.atomic
    def mark_ready_for_dispatch(
        cls,
        *,
        fulfillment,
    ):
        """
        Mark fulfillment ready for dispatch.

        A Delivery is created at this point.

        DispatchPipeline is responsible for:

            - Finding riders
            - Ranking riders
            - Creating offers
            - Assigning the rider
        """

        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )

        cls._ensure_not_terminal(
            fulfillment=fulfillment,
        )

        if fulfillment.status not in [
            OrderFulfillment.Status.PACKING,
            OrderFulfillment.Status.PROCESSING,
        ]:
            raise ValueError(
                "Fulfillment is not currently "
                "being prepared."
            )

        cls._ensure_order_can_fulfill(
            fulfillment=fulfillment,
        )

        cls._validate_fulfillment_items(
            fulfillment=fulfillment,
        )

        packages = list(
            fulfillment.packages.all()
        )

        if not packages:
            raise ValueError(
                "Fulfillment must have at least "
                "one package before dispatch."
            )

        not_ready = [
            package
            for package in packages
            if package.status
            != Package.Status.READY_FOR_PICKUP
        ]

        if not_ready:
            raise ValueError(
                "All packages must be ready for "
                "pickup before dispatch."
            )

        fulfillment.status = (
            OrderFulfillment.Status.READY_FOR_DISPATCH
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

        delivery = cls._create_delivery(
            fulfillment=fulfillment,
        )

        return fulfillment, delivery

    # ==================================================
    # Create Delivery
    # ==================================================

    @classmethod
    def _create_delivery(
        cls,
        *,
        fulfillment,
    ):
        """
        Create the Delivery belonging to this fulfillment.

        Pickup information comes from the immutable
        OrderFulfillment store snapshot.

        Destination information comes from the
        OrderAddress snapshot.
        """

        existing_delivery = (
            Delivery.objects
            .filter(
                fulfillment=fulfillment,
            )
            .first()
        )

        if existing_delivery:
            return existing_delivery

        order = fulfillment.order

        address = cls._get_delivery_address(
            order=order,
        )

        delivery = Delivery.objects.create(

            # ------------------------------------------
            # Fulfillment
            # ------------------------------------------

            fulfillment=fulfillment,

            # ------------------------------------------
            # Customer
            # ------------------------------------------

            customer=order.customer,

            # ------------------------------------------
            # Vendor
            # ------------------------------------------

            vendor=(
                fulfillment.store.vendor
            ),

            # ------------------------------------------
            # Pickup Store
            # ------------------------------------------

            pickup_store=fulfillment.store,

            pickup_store_name=(
                fulfillment.store_name
            ),

            # ------------------------------------------
            # Pickup Snapshot
            # ------------------------------------------

            pickup_latitude=(
                fulfillment.store_latitude
            ),

            pickup_longitude=(
                fulfillment.store_longitude
            ),

            pickup_address=(
                cls._build_pickup_address(
                    fulfillment=fulfillment,
                )
            ),

            # ------------------------------------------
            # Destination Snapshot
            # ------------------------------------------

            destination_latitude=(
                address.latitude
            ),

            destination_longitude=(
                address.longitude
            ),

            destination_address=(
                cls._build_destination_address(
                    address=address,
                )
            ),

            # ------------------------------------------
            # Delivery
            # ------------------------------------------

            delivery_type=(
                Delivery.DeliveryType.INSTANT
            ),

            status=(
                Delivery.DeliveryStatus.PENDING
            ),

            payment_status=(
                Delivery.PaymentStatus.PAID
            ),

            # ------------------------------------------
            # Pricing
            # ------------------------------------------

            estimated_price=(
                fulfillment.delivery_fee
            ),

            actual_price=Decimal("0.00"),

            base_price=Decimal("0.00"),

            distance_price=Decimal("0.00"),

            weight_price=Decimal("0.00"),

            surge_price=Decimal("0.00"),

            discount=(
                fulfillment.discount_amount
            ),

            insurance_fee=(
                fulfillment.insurance_fee
            ),

            service_fee=(
                fulfillment.service_fee
            ),

            total_price=(
                fulfillment.delivery_fee
                + fulfillment.service_fee
                + fulfillment.insurance_fee
            ),

        )

        return delivery

    # ==================================================
    # Delivery Address
    # ==================================================

    @staticmethod
    def _get_delivery_address(
        *,
        order,
    ):
        """
        Retrieve the immutable delivery address
        belonging to the order.

        Adjust `order.delivery_address` if your
        OrderAddress related_name differs.
        """

        try:
            return order.delivery_address
        except AttributeError:

            raise ValueError(
                "Order does not have a delivery address."
            )

    # ==================================================
    # Pickup Address
    # ==================================================

    @staticmethod
    def _build_pickup_address(
        *,
        fulfillment,
    ):
        parts = [
            fulfillment.store_address_line_1,
            fulfillment.store_address_line_2,
            fulfillment.store_city,
            fulfillment.store_state,
            fulfillment.store_country,
            fulfillment.store_postal_code,
        ]

        return ", ".join(
            part
            for part in parts
            if part
        )

    # ==================================================
    # Destination Address
    # ==================================================

    @staticmethod
    def _build_destination_address(
        *,
        address,
    ):
        """
        Convert the OrderAddress snapshot into the
        Delivery destination string.

        Adjust field names to match your OrderAddress.
        """

        parts = [
            getattr(
                address,
                "address_line_1",
                "",
            ),
            getattr(
                address,
                "address_line_2",
                "",
            ),
            getattr(
                address,
                "city",
                "",
            ),
            getattr(
                address,
                "state",
                "",
            ),
            getattr(
                address,
                "country",
                "Nigeria",
            ),
            getattr(
                address,
                "postal_code",
                "",
            ),
        ]

        return ", ".join(
            part
            for part in parts
            if part
        )

    # ==================================================
    # Dispatch
    # ==================================================

    @classmethod
    @transaction.atomic
    def mark_dispatched(
        cls,
        *,
        fulfillment,
    ):
        """
        Mark fulfillment as dispatched after a rider
        has been successfully assigned/accepted.
        """

        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )

        if fulfillment.status != (
            OrderFulfillment.Status.READY_FOR_DISPATCH
        ):
            raise ValueError(
                "Fulfillment is not ready for dispatch."
            )

        delivery = (
            Delivery.objects
            .select_for_update()
            .filter(
                fulfillment=fulfillment,
            )
            .first()
        )

        if delivery is None:
            raise ValueError(
                "Fulfillment does not have "
                "a delivery."
            )

        if delivery.status not in [
            Delivery.DeliveryStatus.RIDER_ASSIGNED,
            Delivery.DeliveryStatus.RIDER_ACCEPTED,
        ]:
            raise ValueError(
                "Delivery must have an assigned "
                "or accepted rider before the "
                "fulfillment can be dispatched."
            )

        fulfillment.status = (
            OrderFulfillment.Status.DISPATCHED
        )

        fulfillment.dispatched_at = (
            timezone.now()
        )

        fulfillment.save(
            update_fields=[
                "status",
                "dispatched_at",
                "updated_at",
            ]
        )

        return fulfillment

    # ==================================================
    # Out For Delivery
    # ==================================================

    @classmethod
    @transaction.atomic
    def mark_out_for_delivery(
        cls,
        *,
        fulfillment,
    ):
        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )

        if fulfillment.status != (
            OrderFulfillment.Status.DISPATCHED
        ):
            raise ValueError(
                "Fulfillment must be dispatched "
                "before going out for delivery."
            )

        fulfillment.status = (
            OrderFulfillment.Status.OUT_FOR_DELIVERY
        )

        fulfillment.out_for_delivery_at = (
            timezone.now()
        )

        fulfillment.save(
            update_fields=[
                "status",
                "out_for_delivery_at",
                "updated_at",
            ]
        )

        return fulfillment

    # ==================================================
    # Delivered
    # ==================================================

    @classmethod
    @transaction.atomic
    def mark_delivered(
        cls,
        *,
        fulfillment,
    ):
        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )

        if fulfillment.status != (
            OrderFulfillment.Status.OUT_FOR_DELIVERY
        ):
            raise ValueError(
                "Fulfillment must be out for delivery "
                "before it can be delivered."
            )

        packages = list(
            fulfillment.packages.all()
        )

        if not packages:
            raise ValueError(
                "Fulfillment has no packages."
            )

        not_delivered = [
            package
            for package in packages
            if package.status
            != Package.Status.DELIVERED
        ]

        if not_delivered:
            raise ValueError(
                "All packages must be delivered "
                "before the fulfillment is "
                "marked delivered."
            )

        fulfillment.status = (
            OrderFulfillment.Status.DELIVERED
        )

        fulfillment.delivered_at = (
            timezone.now()
        )

        fulfillment.save(
            update_fields=[
                "status",
                "delivered_at",
                "updated_at",
            ]
        )

        cls._update_order_status(
            fulfillment=fulfillment,
        )

        return fulfillment

    # ==================================================
    # Cancel
    # ==================================================

    @classmethod
    @transaction.atomic
    def cancel(
        cls,
        *,
        fulfillment,
    ):
        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )

        if fulfillment.status in [
            OrderFulfillment.Status.DELIVERED,
            OrderFulfillment.Status.CANCELLED,
        ]:
            raise ValueError(
                "Fulfillment cannot be cancelled "
                "from its current state."
            )

        fulfillment.status = (
            OrderFulfillment.Status.CANCELLED
        )

        fulfillment.cancelled_at = (
            timezone.now()
        )

        fulfillment.save(
            update_fields=[
                "status",
                "cancelled_at",
                "updated_at",
            ]
        )

        # ----------------------------------------------
        # Cancel delivery
        # ----------------------------------------------

        Delivery.objects.filter(
            fulfillment=fulfillment,
        ).exclude(
            status=Delivery.DeliveryStatus.DELIVERED,
        ).update(
            status=Delivery.DeliveryStatus.CANCELLED,
        )

        return fulfillment

    # ==================================================
    # Validate Items
    # ==================================================

    @staticmethod
    def _validate_fulfillment_items(
        *,
        fulfillment,
    ):
        if not fulfillment.items.exists():

            raise ValueError(
                "Fulfillment must contain at least "
                "one order item."
            )

        invalid_items = (
            fulfillment.items
            .exclude(
                store_id=fulfillment.store_id,
            )
            .exists()
        )

        if invalid_items:

            raise ValueError(
                "Fulfillment contains an item "
                "belonging to another store."
            )

    # ==================================================
    # Validate Order
    # ==================================================

    @staticmethod
    def _ensure_order_can_fulfill(
        *,
        fulfillment,
    ):
        order = fulfillment.order

        if order.payment_status != (
            Order.PaymentStatus.PAID
        ):
            raise ValueError(
                "Order must be paid before the "
                "fulfillment can be processed."
            )

        if order.status in [
            Order.Status.CANCELLED,
            Order.Status.FAILED,
        ]:
            raise ValueError(
                "The order cannot be fulfilled."
            )

    # ==================================================
    # Terminal
    # ==================================================

    @staticmethod
    def _ensure_not_terminal(
        *,
        fulfillment,
    ):
        if fulfillment.status in [
            OrderFulfillment.Status.DELIVERED,
            OrderFulfillment.Status.CANCELLED,
            OrderFulfillment.Status.FAILED,
        ]:
            raise ValueError(
                "Fulfillment is in a terminal state."
            )

    # ==================================================
    # Lock Fulfillment
    # ==================================================

    @staticmethod
    def _lock_fulfillment(
        *,
        fulfillment,
    ):
        return (
            OrderFulfillment.objects
            .select_for_update()
            .select_related(
                "order",
                "store",
                "store__vendor",
            )
            .prefetch_related(
                "items",
                "packages",
            )
            .get(
                pk=fulfillment.pk,
            )
        )

    # ==================================================
    # Lock Package
    # ==================================================

    @staticmethod
    def _lock_package(
        *,
        package,
    ):
        return (
            Package.objects
            .select_for_update()
            .select_related(
                "fulfillment",
                "fulfillment__order",
            )
            .get(
                pk=package.pk,
            )
        )

    # ==================================================
    # Package Number
    # ==================================================

    @staticmethod
    def _generate_package_number():

        return (
            f"PKG-"
            f"{timezone.now():%Y%m%d}-"
            f"{uuid.uuid4().hex[:10].upper()}"
        )

    # ==================================================
    # Package Tracking Number
    # ==================================================

    @staticmethod
    def _generate_package_tracking_number():

        return (
            f"PKG-TRK-"
            f"{uuid.uuid4().hex[:12].upper()}"
        )

    # ==================================================
    # Update Order Status
    # ==================================================

    @classmethod
    def _update_order_status(
        cls,
        *,
        fulfillment,
    ):
        """
        Recalculate the parent Order status based
        on all active fulfillments.
        """

        order = (
            Order.objects
            .select_for_update()
            .get(
                pk=fulfillment.order_id,
            )
        )

        fulfillments = list(
            order.fulfillments.all()
        )

        if not fulfillments:
            return

        active_fulfillments = [
            item
            for item in fulfillments
            if item.status
            != OrderFulfillment.Status.CANCELLED
        ]

        if not active_fulfillments:
            return

        # ----------------------------------------------
        # All delivered
        # ----------------------------------------------

        if all(
            item.status
            == OrderFulfillment.Status.DELIVERED
            for item in active_fulfillments
        ):

            order.status = (
                Order.Status.DELIVERED
            )

            order.delivered_at = (
                timezone.now()
            )

            order.save(
                update_fields=[
                    "status",
                    "delivered_at",
                    "updated_at",
                ]
            )

            return

        # ----------------------------------------------
        # Any out for delivery
        # ----------------------------------------------

        if any(
            item.status
            == OrderFulfillment.Status.OUT_FOR_DELIVERY
            for item in active_fulfillments
        ):

            order.status = (
                Order.Status.OUT_FOR_DELIVERY
            )

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            return

        # ----------------------------------------------
        # Any dispatched
        # ----------------------------------------------

        if any(
            item.status
            == OrderFulfillment.Status.DISPATCHED
            for item in active_fulfillments
        ):

            order.status = (
                Order.Status.PROCESSING
            )

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            return

        # ----------------------------------------------
        # Any ready
        # ----------------------------------------------

        if any(
            item.status
            == OrderFulfillment.Status.READY_FOR_DISPATCH
            for item in active_fulfillments
        ):

            order.status = (
                Order.Status.READY_FOR_DISPATCH
            )

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            return

        # ----------------------------------------------
        # Any processing
        # ----------------------------------------------

        if any(
            item.status
            in [
                OrderFulfillment.Status.PROCESSING,
                OrderFulfillment.Status.PACKING,
            ]
            for item in active_fulfillments
        ):

            order.status = (
                Order.Status.PROCESSING
            )

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )