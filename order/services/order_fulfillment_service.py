from decimal import Decimal

import logging
import secrets
import uuid

from django.db import transaction
from django.utils import timezone

from common.services.refund_service import RefundService
from deliveries.dispatch.assignment import AssignmentService
from deliveries.models import (
    Delivery,
    DeliveryAssignment,
)
from deliveries.services.delivery_service import DeliveryService
from notifications.services import NotificationService

from ..models import (
    Order,
    OrderFulfillment,
    OrderItem,
    Package,
)


logger = logging.getLogger(__name__)


# ==================================================
# OTP configuration
# ==================================================

OTP_LENGTH = 6
OTP_MAX_ATTEMPTS = 5


def _generate_otp() -> str:
    """
    Cryptographically secure 6-digit OTP.

    Uses secrets.randbelow so the value is unpredictable.
    """
    return f"{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}"


class OrderFulfillmentService:
    """
    Coordinates the lifecycle of an OrderFulfillment.

    Delivery creation is delegated to
    DeliveryService.create_delivery. This service does not
    duplicate route, pricing, or dispatch logic.

    Delivery OTP
    ------------
    A 6-digit OTP is generated on the fulfillment when it
    enters OUT_FOR_DELIVERY — that is, when the rider has
    physically left the store with the package and is en
    route to the customer. The OTP is delivered to the
    customer via SMS and push at that moment. The assigned
    rider must enter it at handover to mark the
    fulfillment delivered.

    OTPs are per-fulfillment (per-store delivery). A
    multi-store order produces one OTP per store, and
    each rider verifies only their own assignment.

    Why OUT_FOR_DELIVERY (not READY_FOR_DISPATCH)
    ---------------------------------------------
    Issuing the OTP at READY_FOR_DISPATCH means the
    customer receives it potentially hours before a rider
    is even assigned, and again after any cancel-and-
    restart cycle. Issuing at OUT_FOR_DELIVERY keeps the
    code fresh and valid only for the delivery in
    progress.
    """

    # ==================================================
    # Start Processing
    # ==================================================

    @classmethod
    @transaction.atomic
    def start_processing(cls, *, fulfillment):

        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )
        cls._ensure_not_terminal(fulfillment=fulfillment)

        if (
            fulfillment.status
            != OrderFulfillment.Status.PENDING
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
        fulfillment.processing_at = timezone.now()

        fulfillment.save(
            update_fields=[
                "status",
                "processing_at",
                "updated_at",
            ],
        )

        return fulfillment

    # ==================================================
    # Start Packing
    # ==================================================

    @classmethod
    @transaction.atomic
    def start_packing(cls, *, fulfillment):

        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )
        cls._ensure_not_terminal(fulfillment=fulfillment)

        if (
            fulfillment.status
            != OrderFulfillment.Status.PROCESSING
        ):
            raise ValueError(
                "Fulfillment must be processing before "
                "packing can begin."
            )

        cls._ensure_order_can_fulfill(
            fulfillment=fulfillment,
        )

        fulfillment.status = (
            OrderFulfillment.Status.PACKING
        )
        fulfillment.packing_at = timezone.now()

        fulfillment.save(
            update_fields=[
                "status",
                "packing_at",
                "updated_at",
            ],
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

        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )

        if fulfillment.status not in [
            OrderFulfillment.Status.PROCESSING,
            OrderFulfillment.Status.PACKING,
        ]:
            raise ValueError(
                "Packages can only be created while the "
                "fulfillment is being prepared."
            )

        cls._ensure_order_can_fulfill(
            fulfillment=fulfillment,
        )

        cls._validate_package_values(
            weight=weight,
            length=length,
            width=width,
            height=height,
            declared_value=declared_value,
        )

        return Package.objects.create(
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
                "Fulfillment is not currently being "
                "prepared."
            )

        package.status = Package.Status.PACKING
        package.save(
            update_fields=["status", "updated_at"],
        )

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
                "Package cannot be marked as packed "
                "from its current state."
            )

        package.status = Package.Status.PACKED
        package.packed_at = timezone.now()

        package.save(
            update_fields=[
                "status",
                "packed_at",
                "updated_at",
            ],
        )

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
                "Package must be packed before it can "
                "be ready for pickup."
            )

        package.status = (
            Package.Status.READY_FOR_PICKUP
        )
        package.ready_for_pickup_at = timezone.now()

        package.save(
            update_fields=[
                "status",
                "ready_for_pickup_at",
                "updated_at",
            ],
        )

        cls._maybe_auto_ready_for_dispatch(
            package=package,
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
        DeliveryService.create_delivery.

        NOTE: The delivery OTP is NOT generated here. It is
        generated when the fulfillment transitions to
        OUT_FOR_DELIVERY (rider is en route).
        """

        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )
        cls._ensure_not_terminal(fulfillment=fulfillment)

        if fulfillment.status not in [
            OrderFulfillment.Status.PACKING,
            OrderFulfillment.Status.PROCESSING,
        ]:
            raise ValueError(
                "Fulfillment is not currently being "
                "prepared."
            )

        cls._ensure_order_can_fulfill(
            fulfillment=fulfillment,
        )
        cls._validate_fulfillment_items(
            fulfillment=fulfillment,
        )

        packages = list(fulfillment.packages.all())

        if not packages:
            raise ValueError(
                "Fulfillment must have at least one "
                "package before dispatch."
            )

        not_ready = [
            package
            for package in packages
            if (
                package.status
                != Package.Status.READY_FOR_PICKUP
            )
        ]

        if not_ready:
            raise ValueError(
                "All packages must be ready for pickup "
                "before dispatch."
            )

        fulfillment.status = (
            OrderFulfillment.Status.READY_FOR_DISPATCH
        )
        fulfillment.ready_for_dispatch_at = timezone.now()

        fulfillment.save(
            update_fields=[
                "status",
                "ready_for_dispatch_at",
                "updated_at",
            ],
        )

        delivery = cls._create_delivery(
            fulfillment=fulfillment,
        )

        return fulfillment, delivery

    # ==================================================
    # Create Delivery (delegates to DeliveryService)
    # ==================================================

    @classmethod
    def _create_delivery(cls, *, fulfillment):

        existing = (
            Delivery.objects
            .select_for_update()
            .filter(fulfillment=fulfillment)
            .first()
        )

        if existing:
            return existing

        destination = cls._build_destination_data(
            fulfillment=fulfillment,
        )

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

        return {
            "address_line_1": (
                fulfillment.delivery_address_line_1
            ),
            "address_line_2": (
                fulfillment.delivery_address_line_2
            ),
            "city": fulfillment.delivery_city,
            "state": fulfillment.delivery_state,
            "country": fulfillment.delivery_country,
            "postal_code": (
                fulfillment.delivery_postal_code
            ),
            "latitude": fulfillment.delivery_latitude,
            "longitude": fulfillment.delivery_longitude,
            "instructions": (
                fulfillment.delivery_instructions or ""
            ),
            "contact_name": (
                fulfillment.delivery_contact_name
            ),
            "contact_phone": (
                fulfillment.delivery_contact_phone
            ),
        }

    # ==================================================
    # OTP: ensure
    # ==================================================

    @staticmethod
    def _ensure_delivery_otp(*, fulfillment) -> str:
        """
        Return the fulfillment's delivery OTP, generating a
        fresh one if it has not been set yet.

        Idempotent within a single dispatch cycle. The OTP
        is cleared when the fulfillment is cancelled or
        failed, so a re-dispatched fulfillment gets a new
        code.
        """

        if fulfillment.delivery_otp:
            return fulfillment.delivery_otp

        otp = _generate_otp()

        fulfillment.delivery_otp = otp
        fulfillment.delivery_otp_generated_at = (
            timezone.now()
        )
        fulfillment.delivery_otp_attempts = 0

        fulfillment.save(
            update_fields=[
                "delivery_otp",
                "delivery_otp_generated_at",
                "delivery_otp_attempts",
                "updated_at",
            ],
        )

        return otp

    # ==================================================
    # OTP: notify customer
    # ==================================================

    @staticmethod
    def _notify_customer_delivery_otp(
        *,
        fulfillment,
        otp,
    ):
        """
        Send the OTP to the customer via SMS and push.

        Best-effort. A failure here does not roll back the
        state transition.
        """

        try:

            order = fulfillment.order
            customer = order.customer

            if customer is None:
                return

            NotificationService.notify(
                user=customer,
                title="Delivery Verification Code",
                message=(
                    f"Your delivery code for order "
                    f"{order.order_number} from "
                    f"{fulfillment.store_name} is {otp}. "
                    f"Share it with the rider only after "
                    f"you receive your package."
                ),
                notification_type="DELIVERY",
                data={
                    "order_id": str(order.pk),
                    "order_number": order.order_number,
                    "fulfillment_id": str(fulfillment.pk),
                    "store_id": str(fulfillment.store_id),
                    "otp_type": "delivery",
                },
                send_email=False,
                send_sms=True,
                send_push=True,
            )

        except Exception:

            logger.exception(
                "Delivery OTP notification failed for "
                "fulfillment %s",
                fulfillment.pk,
            )

    # ==================================================
    # OTP: verify (rider-facing)
    # ==================================================

    @classmethod
    @transaction.atomic
    def verify_delivery_otp(
        cls,
        *,
        rider,
        delivery,
        otp,
    ):
        """
        Rider confirms handover by entering the OTP the
        customer received for this fulfillment.

        Lock order (matching AssignmentService):

            Delivery
                ↓
            DeliveryAssignment
                ↓
            OrderFulfillment

        On success:
            - The active DeliveryAssignment is completed,
              marking the Delivery DELIVERED and restoring
              the rider's availability.
            - All packages on the fulfillment are marked
              DELIVERED.
            - The fulfillment is marked DELIVERED and its
              OTP is cleared.
            - The order is recalculated; it becomes
              DELIVERED once all its active fulfillments
              are delivered.

        On failure:
            - Increments the attempt counter.
            - Locks the fulfillment after OTP_MAX_ATTEMPTS.

        Raises ValueError on any business rule violation.
        """

        if rider is None:
            raise ValueError("Rider is required.")

        if delivery is None:
            raise ValueError("Delivery is required.")

        # --------------------------------------------------
        # Lock order: Delivery → DeliveryAssignment →
        # OrderFulfillment.
        # --------------------------------------------------

        delivery = (
            Delivery.objects
            .select_for_update()
            .select_related("fulfillment")
            .get(pk=delivery.pk)
        )

        assignment = (
            DeliveryAssignment.objects
            .select_for_update()
            .filter(
                delivery_id=delivery.pk,
                rider=rider,
                is_active=True,
            )
            .first()
        )

        if assignment is None:
            raise ValueError(
                "You are not assigned to this delivery."
            )

        fulfillment = cls._lock_fulfillment(
            fulfillment=delivery.fulfillment,
        )
        cls._ensure_not_terminal(fulfillment=fulfillment)

        if (
            fulfillment.status
            != OrderFulfillment.Status.OUT_FOR_DELIVERY
        ):
            raise ValueError(
                "Fulfillment is not out for delivery."
            )

        # --------------------------------------------------
        # Idempotent: already verified.
        # --------------------------------------------------

        if fulfillment.delivery_otp_verified_at is not None:
            return fulfillment

        # --------------------------------------------------
        # Attempts cap.
        # --------------------------------------------------

        if (
            fulfillment.delivery_otp_attempts
            >= OTP_MAX_ATTEMPTS
        ):
            raise ValueError(
                "Too many failed attempts. Contact support."
            )

        # --------------------------------------------------
        # Compare.
        # --------------------------------------------------

        submitted = (otp or "").strip()

        if not fulfillment.delivery_otp:
            raise ValueError(
                "No delivery OTP has been issued."
            )

        if submitted != fulfillment.delivery_otp:

            fulfillment.delivery_otp_attempts += 1
            fulfillment.save(
                update_fields=[
                    "delivery_otp_attempts",
                    "updated_at",
                ],
            )

            logger.warning(
                "Invalid delivery OTP for fulfillment %s "
                "(attempt %s, rider=%s).",
                fulfillment.pk,
                fulfillment.delivery_otp_attempts,
                rider.pk,
            )

            raise ValueError("Invalid OTP.")

        # --------------------------------------------------
        # OTP valid. Complete the assignment first.
        # --------------------------------------------------

        AssignmentService.complete(assignment=assignment)

        now = timezone.now()

        # --------------------------------------------------
        # Mark all packages DELIVERED.
        # --------------------------------------------------

        for package in fulfillment.packages.all():

            if package.status == Package.Status.DELIVERED:
                continue

            package.status = Package.Status.DELIVERED
            package.delivered_at = now

            package.save(
                update_fields=[
                    "status",
                    "delivered_at",
                    "updated_at",
                ],
            )

        # --------------------------------------------------
        # Mark the fulfillment DELIVERED, clear the OTP.
        # --------------------------------------------------

        fulfillment.status = (
            OrderFulfillment.Status.DELIVERED
        )
        fulfillment.delivered_at = now
        fulfillment.delivery_otp_verified_at = now
        fulfillment.delivery_otp = ""

        fulfillment.save(
            update_fields=[
                "status",
                "delivered_at",
                "delivery_otp_verified_at",
                "delivery_otp",
                "updated_at",
            ],
        )

        # --------------------------------------------------
        # Recalculate order status.
        # --------------------------------------------------

        cls._update_order_status(
            fulfillment=fulfillment,
        )

        # --------------------------------------------------
        # Notify customer (best-effort).
        # --------------------------------------------------

        cls._notify_delivery_confirmed(
            fulfillment=fulfillment,
        )

        return fulfillment

    # ==================================================
    # Delivery confirmed notification
    # ==================================================

    @staticmethod
    def _notify_delivery_confirmed(*, fulfillment):

        try:

            order = fulfillment.order
            customer = order.customer

            if customer is None:
                return

            NotificationService.notify(
                user=customer,
                title="Delivery Confirmed",
                message=(
                    f"Your delivery from "
                    f"{fulfillment.store_name} for order "
                    f"{order.order_number} has been "
                    f"confirmed. Thank you!"
                ),
                notification_type="DELIVERY",
                data={
                    "order_id": str(order.pk),
                    "order_number": order.order_number,
                    "fulfillment_id": str(fulfillment.pk),
                    "store_id": str(fulfillment.store_id),
                },
                send_email=False,
                send_sms=False,
                send_push=True,
            )

        except Exception:

            logger.exception(
                "Delivery-confirmed notification failed "
                "for fulfillment %s",
                fulfillment.pk,
            )

    # ==================================================
    # Dispatch
    # ==================================================

    @classmethod
    @transaction.atomic
    def mark_dispatched(cls, *, fulfillment):

        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )

        if (
            fulfillment.status
            != OrderFulfillment.Status.READY_FOR_DISPATCH
        ):
            raise ValueError(
                "Fulfillment is not ready for dispatch."
            )

        delivery = (
            Delivery.objects
            .select_for_update()
            .filter(fulfillment=fulfillment)
            .first()
        )

        if delivery is None:
            raise ValueError(
                "Fulfillment does not have a delivery."
            )

        if delivery.status not in [
            Delivery.DeliveryStatus.RIDER_ASSIGNED,
            Delivery.DeliveryStatus.RIDER_ACCEPTED,
        ]:
            raise ValueError(
                "Delivery must have an assigned or "
                "accepted rider before the fulfillment "
                "can be dispatched."
            )

        fulfillment.status = (
            OrderFulfillment.Status.DISPATCHED
        )
        fulfillment.dispatched_at = timezone.now()

        fulfillment.save(
            update_fields=[
                "status",
                "dispatched_at",
                "updated_at",
            ],
        )

        return fulfillment

    # ==================================================
    # Out For Delivery
    # ==================================================

    @classmethod
    @transaction.atomic
    def mark_out_for_delivery(cls, *, fulfillment):
        """
        Mark fulfillment OUT_FOR_DELIVERY.

        This is the trigger point for the delivery OTP:

            1. Generate the OTP (idempotent).
            2. Transition the fulfillment.
            3. Notify the customer via SMS and push.

        The OTP is delivered at this point because the
        rider has physically left the store and is en route.
        """

        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )

        if (
            fulfillment.status
            != OrderFulfillment.Status.DISPATCHED
        ):
            raise ValueError(
                "Fulfillment must be dispatched before "
                "going out for delivery."
            )

        # --------------------------------------------------
        # Generate the delivery OTP (idempotent).
        # --------------------------------------------------

        otp = cls._ensure_delivery_otp(
            fulfillment=fulfillment,
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
            ],
        )

        # --------------------------------------------------
        # Notify customer of their delivery OTP.
        # --------------------------------------------------

        cls._notify_customer_delivery_otp(
            fulfillment=fulfillment,
            otp=otp,
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
        cancelled_by=None,
        reason="",
    ):

        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )

        if fulfillment.status in [
            OrderFulfillment.Status.DELIVERED,
            OrderFulfillment.Status.CANCELLED,
        ]:
            raise ValueError(
                "Fulfillment cannot be cancelled from "
                "its current state."
            )

        fulfillment.status = (
            OrderFulfillment.Status.CANCELLED
        )
        fulfillment.cancelled_at = timezone.now()

        # --------------------------------------------------
        # Clear the OTP.
        #
        # A cancelled fulfillment must not carry an OTP
        # into any subsequent re-dispatch. If it is
        # restarted, a fresh code is generated at
        # OUT_FOR_DELIVERY.
        # --------------------------------------------------

        fulfillment.delivery_otp = ""
        fulfillment.delivery_otp_generated_at = None
        fulfillment.delivery_otp_verified_at = None
        fulfillment.delivery_otp_attempts = 0

        fulfillment.save(
            update_fields=[
                "status",
                "cancelled_at",
                "delivery_otp",
                "delivery_otp_generated_at",
                "delivery_otp_verified_at",
                "delivery_otp_attempts",
                "updated_at",
            ],
        )

        AssignmentService.cancel_fulfillment(
            fulfillment=fulfillment,
            cancelled_by=cancelled_by,
            reason=(
                reason or "Fulfillment cancelled."
            ),
        )

        return fulfillment

    # ==================================================
    # Vendor cannot fulfill
    # ==================================================

    @classmethod
    @transaction.atomic
    def vendor_cannot_fulfill(
        cls,
        *,
        fulfillment,
        failed_items=None,
        reason="",
        failed_by=None,
    ):

        fulfillment = cls._lock_fulfillment(
            fulfillment=fulfillment,
        )
        cls._ensure_not_terminal(fulfillment=fulfillment)

        if failed_items is None:

            failed_items = list(
                fulfillment.items
                .filter(
                    fulfillment_status=(
                        OrderItem
                        .FulfillmentStatus
                        .PENDING
                    )
                )
            )

        else:

            for item in failed_items:

                if item.fulfillment_id != fulfillment.pk:
                    raise ValueError(
                        f"OrderItem {item.pk} does not "
                        f"belong to fulfillment "
                        f"{fulfillment.pk}."
                    )

                if item.fulfillment_status != (
                    OrderItem.FulfillmentStatus.PENDING
                ):
                    raise ValueError(
                        f"OrderItem {item.pk} is not "
                        "PENDING; it cannot be marked "
                        "unavailable."
                    )

        if not failed_items:
            raise ValueError(
                "No items to mark as unavailable."
            )

        if not reason:
            raise ValueError(
                "A reason is required when marking "
                "items unavailable."
            )

        item_ids = [item.pk for item in failed_items]

        OrderItem.objects.filter(
            pk__in=item_ids,
        ).update(
            fulfillment_status=(
                OrderItem.FulfillmentStatus.UNAVAILABLE
            ),
            unavailable_reason=reason,
        )

        for item in failed_items:
            item.refresh_from_db()

        has_remaining_pending = (
            fulfillment.items
            .filter(
                fulfillment_status=(
                    OrderItem.FulfillmentStatus.PENDING
                )
            )
            .exists()
        )

        has_remaining_fulfilled = (
            fulfillment.items
            .filter(
                fulfillment_status=(
                    OrderItem.FulfillmentStatus.FULFILLED
                )
            )
            .exists()
        )

        refund_transaction = (
            RefundService.refund_fulfillment(
                fulfillment=fulfillment,
                reason=reason,
            )
        )

        if (
            not has_remaining_fulfilled
            and not has_remaining_pending
        ):

            fulfillment.status = (
                OrderFulfillment.Status.FAILED
            )
            fulfillment.cancelled_at = timezone.now()

            # ----------------------------------------------
            # Clear the OTP.
            #
            # A FAILED fulfillment carries no valid OTP
            # into any future workflow.
            # ----------------------------------------------

            fulfillment.delivery_otp = ""
            fulfillment.delivery_otp_generated_at = None
            fulfillment.delivery_otp_verified_at = None
            fulfillment.delivery_otp_attempts = 0

            fulfillment.save(
                update_fields=[
                    "status",
                    "cancelled_at",
                    "delivery_otp",
                    "delivery_otp_generated_at",
                    "delivery_otp_verified_at",
                    "delivery_otp_attempts",
                    "updated_at",
                ],
            )

            try:

                AssignmentService.cancel_fulfillment(
                    fulfillment=fulfillment,
                    cancelled_by=failed_by,
                    reason=reason,
                )

            except Exception:

                logger.exception(
                    "Delivery cancellation failed for "
                    "fulfillment %s",
                    fulfillment.pk,
                )

        cls._notify_vendor_failure(
            fulfillment=fulfillment,
            failed_items=failed_items,
            reason=reason,
            refund_transaction=refund_transaction,
        )

        cls._update_order_status(
            fulfillment=fulfillment,
        )

        return fulfillment

    # ==================================================
    # Vendor failure notification
    # ==================================================

    @classmethod
    def _notify_vendor_failure(
        cls,
        *,
        fulfillment,
        failed_items,
        reason,
        refund_transaction,
    ):

        try:

            order = fulfillment.order
            customer = order.customer

            if customer is None:
                return

            unavailable_names = [
                item.display_name
                for item in failed_items
            ]

            perishable_total = sum(
                (
                    Decimal(str(item.subtotal))
                    for item in failed_items
                    if not item.is_refundable
                ),
                Decimal("0.00"),
            )

            refund_total = (
                Decimal(str(refund_transaction.amount))
                if refund_transaction is not None
                else Decimal("0.00")
            )

            message_parts = [
                f"Unfortunately, "
                f"{fulfillment.store_name} could not "
                f"fulfill part of your order "
                f"{order.order_number}.",
            ]

            if unavailable_names:
                message_parts.append(
                    "Unavailable items: "
                    + ", ".join(unavailable_names)
                    + "."
                )

            if refund_total > Decimal("0.00"):
                message_parts.append(
                    f"₦{refund_total} has been credited "
                    "to your wallet."
                )

            if perishable_total > Decimal("0.00"):
                message_parts.append(
                    f"₦{perishable_total} of perishable "
                    "items could not be refunded per "
                    "our policy."
                )

            NotificationService.notify(
                user=customer,
                title="Order Update",
                message=" ".join(message_parts),
                notification_type="DELIVERY",
                data={
                    "order_id": str(order.pk),
                    "order_number": order.order_number,
                    "fulfillment_id": str(fulfillment.pk),
                    "refund_amount": str(refund_total),
                    "perishable_amount": str(
                        perishable_total,
                    ),
                },
                send_email=True,
                send_sms=False,
                send_push=True,
            )

        except Exception:

            logger.exception(
                "Customer notification failed for "
                "vendor failure on fulfillment %s",
                fulfillment.pk,
            )

    # ==================================================
    # Validate Items
    # ==================================================

    @staticmethod
    def _validate_fulfillment_items(*, fulfillment):

        if not fulfillment.items.exists():

            raise ValueError(
                "Fulfillment must contain at least one "
                "order item."
            )

        invalid_items = (
            fulfillment.items
            .exclude(store_id=fulfillment.store_id)
            .exists()
        )

        if invalid_items:

            raise ValueError(
                "Fulfillment contains an item belonging "
                "to another store."
            )

    # ==================================================
    # Validate Package Values
    # ==================================================

    @staticmethod
    def _validate_package_values(
        *,
        weight,
        length,
        width,
        height,
        declared_value,
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
                    f"{field_name.replace('_', ' ').capitalize()} "
                    "cannot be negative."
                )

    # ==================================================
    # Validate Order
    # ==================================================

    @staticmethod
    def _ensure_order_can_fulfill(*, fulfillment):

        order = fulfillment.order

        if (
            order.payment_status
            != Order.PaymentStatus.PAID
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
    def _ensure_not_terminal(*, fulfillment):

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
    def _lock_fulfillment(*, fulfillment):

        return (
            OrderFulfillment.objects
            .select_for_update()
            .select_related(
                "order",
                "store",
                "store__vendor",
            )
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
            .select_related(
                "fulfillment",
                "fulfillment__order",
            )
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

        return (
            f"PKG-TRK-{uuid.uuid4().hex[:12].upper()}"
        )

    # ==================================================
    # Auto Ready-For-Dispatch
    # ==================================================

    @classmethod
    def _maybe_auto_ready_for_dispatch(cls, *, package):

        try:

            fulfillment = cls._lock_fulfillment(
                fulfillment=package.fulfillment,
            )

            if (
                fulfillment.status
                != OrderFulfillment.Status.PACKING
            ):
                return

            has_not_ready = (
                fulfillment.packages
                .exclude(
                    status=(
                        Package.Status.READY_FOR_PICKUP
                    )
                )
                .exists()
            )

            if has_not_ready:
                return

            if not fulfillment.packages.exists():
                return

            cls.mark_ready_for_dispatch(
                fulfillment=fulfillment,
            )

        except Exception:

            logger.exception(
                "Auto ready-for-dispatch failed for "
                "fulfillment %s",
                getattr(
                    package.fulfillment,
                    "pk",
                    None,
                ),
            )

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

        fulfillments = list(
            order.fulfillments.all()
        )

        if not fulfillments:
            return

        active = [
            item
            for item in fulfillments
            if (
                item.status
                != OrderFulfillment.Status.CANCELLED
            )
        ]

        if not active:
            return

        if all(
            item.status
            == OrderFulfillment.Status.DELIVERED
            for item in active
        ):
            order.status = Order.Status.DELIVERED
            order.delivered_at = timezone.now()
            order.save(
                update_fields=[
                    "status",
                    "delivered_at",
                    "updated_at",
                ],
            )
            return

        if any(
            item.status
            == OrderFulfillment.Status.OUT_FOR_DELIVERY
            for item in active
        ):
            order.status = (
                Order.Status.OUT_FOR_DELIVERY
            )
            order.save(
                update_fields=["status", "updated_at"],
            )
            return

        if any(
            item.status
            == OrderFulfillment.Status.DISPATCHED
            for item in active
        ):
            order.status = Order.Status.PROCESSING
            order.save(
                update_fields=["status", "updated_at"],
            )
            return

        if any(
            item.status
            == OrderFulfillment.Status.READY_FOR_DISPATCH
            for item in active
        ):
            order.status = (
                Order.Status.READY_FOR_DISPATCH
            )
            order.save(
                update_fields=["status", "updated_at"],
            )
            return

        if any(
            item.status in [
                OrderFulfillment.Status.PROCESSING,
                OrderFulfillment.Status.PACKING,
            ]
            for item in active
        ):
            order.status = Order.Status.PROCESSING
            order.save(
                update_fields=["status", "updated_at"],
            )
            return

        if any(
            item.status
            == OrderFulfillment.Status.PENDING
            for item in active
        ):
            order.status = Order.Status.PENDING
            order.save(
                update_fields=["status", "updated_at"],
            )
            return