import logging

from django.db import transaction


logger = logging.getLogger(__name__)


class DispatchNotifier:
    """
    Dispatch domain notification gateway.

    Responsibilities
    ----------------
    • Translate dispatch events into notification requests.
    • Notify riders, customers, vendors, and administrators.
    • Keep notification-channel decisions close to the
      dispatch domain.

    NotificationService is responsible for actually
    delivering notifications through the configured
    channels.

    This class does NOT:
        • Create notifications directly.
        • Send FCM requests directly.
        • Send emails directly.
        • Send SMS directly.

    Notification failures are intentionally isolated
    from the dispatch lifecycle.
    """

    # ==================================================
    # Delivery Offer
    # ==================================================

    @classmethod
    def offer_delivery(cls, offer):
        if offer is None:
            return

        rider = getattr(offer, "rider", None)
        delivery = getattr(offer, "delivery", None)

        if rider is None or delivery is None:
            return

        expires_at = getattr(offer, "expires_at", None)

        cls._safe_notify(
            user=rider,
            title="New Delivery Request",
            message=(
                "You have a new delivery request "
                "waiting for your response."
            ),
            notification_type="DELIVERY_OFFER",
            data={
                "offer_id": str(offer.id),
                "delivery_id": str(delivery.id),
                "expires_at": (
                    expires_at.isoformat() if expires_at else None
                ),
            },
            send_push=True,
            send_sms=True,
        )

    # ==================================================
    # Rider Assigned
    # ==================================================

    @classmethod
    def notify_rider(cls, assignment):
        if assignment is None:
            return

        rider = getattr(assignment, "rider", None)
        delivery = getattr(assignment, "delivery", None)

        if rider is None or delivery is None:
            return

        cls._safe_notify(
            user=rider,
            title="Delivery Assigned",
            message="A delivery has been assigned to you.",
            notification_type="DELIVERY",
            data={
                "assignment_id": str(assignment.id),
                "delivery_id": str(delivery.id),
            },
            send_push=True,
            send_sms=True,
        )

    # ==================================================
    # Customer - Rider Assigned
    # ==================================================

    @classmethod
    def notify_customer(cls, assignment):
        if assignment is None:
            return

        delivery = getattr(assignment, "delivery", None)
        rider = getattr(assignment, "rider", None)

        if delivery is None or rider is None:
            return

        customer = getattr(delivery, "customer", None)
        if customer is None:
            return

        rider_name = (
            rider.get_full_name()
            or getattr(rider, "email", None)
            or "Your rider"
        )

        cls._safe_notify(
            user=customer,
            title="Rider Assigned",
            message=f"{rider_name} has been assigned to your delivery.",
            notification_type="DELIVERY",
            data={
                "assignment_id": str(assignment.id),
                "delivery_id": str(delivery.id),
                "rider_id": str(rider.id),
            },
            send_email=True,
            send_push=True,
        )

    # ==================================================
    # Vendor - Rider Assigned
    # ==================================================

    @classmethod
    def notify_vendor(cls, assignment):
        if assignment is None:
            return

        delivery = getattr(assignment, "delivery", None)
        if delivery is None:
            return

        vendor = getattr(delivery, "vendor", None)
        if vendor is None:
            return

        vendor_user = getattr(vendor, "user", None)
        if vendor_user is None:
            return

        cls._safe_notify(
            user=vendor_user,
            title="Rider Assigned",
            message="A rider has been assigned for pickup.",
            notification_type="DELIVERY",
            data={
                "assignment_id": str(assignment.id),
                "delivery_id": str(delivery.id),
            },
            send_push=True,
            send_email=True,
        )

    # ==================================================
    # Offer Rejected
    # ==================================================

    @classmethod
    def notify_offer_rejected(cls, offer):
        """
        Internal/customer-facing hook for offer rejection.

        By default the rider is NOT notified because the rider
        initiated the rejection.
        """
        if offer is None:
            return
        delivery = getattr(offer, "delivery", None)
        if delivery is None:
            return
        # No-op by design; kept as a domain hook.
        return

    # ==================================================
    # Offer Expired
    # ==================================================

    @classmethod
    def notify_offer_expired(cls, offer):
        if offer is None:
            return

        rider = getattr(offer, "rider", None)
        delivery = getattr(offer, "delivery", None)

        if rider is None or delivery is None:
            return

        cls._safe_notify(
            user=rider,
            title="Delivery Offer Expired",
            message=(
                "This delivery offer expired before "
                "a response was received."
            ),
            notification_type="DELIVERY_OFFER",
            data={
                "offer_id": str(offer.id),
                "delivery_id": str(delivery.id),
            },
            send_push=True,
        )

    # ==================================================
    # Dispatch Failed
    # ==================================================

    @classmethod
    def notify_dispatch_failed(
        cls,
        delivery,
        result=None,
        exception=None,
    ):
        """
        Notify the customer that dispatch currently cannot
        find an eligible rider.

        `result` and `exception` are accepted for API symmetry
        with the coordinator's call shape, but are not used
        in the notification payload.
        """
        if delivery is None:
            return

        customer = getattr(delivery, "customer", None)
        if customer is None:
            return

        cls._safe_notify(
            user=customer,
            title="Finding a Rider",
            message=(
                "We're currently unable to assign a rider. "
                "We'll continue searching automatically."
            ),
            notification_type="DELIVERY",
            data={"delivery_id": str(delivery.id)},
            send_email=True,
            send_push=True,
        )

    # ==================================================
    # Dispatch Cancelled
    # ==================================================

    @classmethod
    def notify_dispatch_cancelled(cls, delivery):
        if delivery is None:
            return

        customer = getattr(delivery, "customer", None)
        if customer is None:
            return

        cls._safe_notify(
            user=customer,
            title="Dispatch Cancelled",
            message=(
                "The dispatch process for your delivery "
                "has been cancelled."
            ),
            notification_type="DELIVERY",
            data={"delivery_id": str(delivery.id)},
            send_email=True,
            send_push=True,
        )

    # ==================================================
    # Redispatch Started
    # ==================================================

    @classmethod
    def notify_redispatch(cls, delivery):
        if delivery is None:
            return

        customer = getattr(delivery, "customer", None)
        if customer is None:
            return

        cls._safe_notify(
            user=customer,
            title="Finding Another Rider",
            message=(
                "We're looking for another rider "
                "for your delivery."
            ),
            notification_type="DELIVERY",
            data={"delivery_id": str(delivery.id)},
            send_push=True,
        )

    # ==================================================
    # Coordinator-compatible aliases
    # ==================================================
    #
    # DispatchCoordinator invokes these names directly. They
    # forward to the canonical notify_* methods.
    # ==================================================

    @classmethod
    def offer_rejected(cls, offer):
        return cls.notify_offer_rejected(offer=offer)

    @classmethod
    def offer_expired(cls, offer):
        return cls.notify_offer_expired(offer=offer)

    @classmethod
    def dispatch_failed(cls, delivery, result=None, exception=None):
        return cls.notify_dispatch_failed(
            delivery=delivery,
            result=result,
            exception=exception,
        )

    @classmethod
    def dispatch_cancelled(cls, delivery):
        return cls.notify_dispatch_cancelled(delivery=delivery)

    @classmethod
    def redispatch(cls, delivery):
        return cls.notify_redispatch(delivery=delivery)

    # ==================================================
    # Internal Notification Gateway
    # ==================================================

    @classmethod
    def _notify(
        cls,
        *,
        user,
        title,
        message,
        notification_type,
        data=None,
        send_email=False,
        send_sms=False,
        send_push=False,
    ):
        if user is None:
            return

        from notifications.services import NotificationService

        NotificationService.notify(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            data=data or {},
            send_email=send_email,
            send_sms=send_sms,
            send_push=send_push,
        )

    # ==================================================
    # Safe Notification
    # ==================================================

    @classmethod
    def _safe_notify(cls, **kwargs):
        """
        Execute a notification without allowing a
        notification-channel failure to break the
        dispatch workflow.

        Failures are logged but do not propagate.
        """
        try:
            cls._notify(**kwargs)
        except Exception:
            logger.exception(
                "Dispatch notification failed (best effort)."
            )
            return

    # ==================================================
    # Assignment Notifications
    # ==================================================

    @classmethod
    def schedule_assignment_notifications(cls, assignment):
        """
        Schedule assignment notifications to execute only
        after the surrounding transaction commits.
        """
        if assignment is None:
            return

        transaction.on_commit(
            lambda: cls._send_assignment_notifications(assignment)
        )

    @classmethod
    def _send_assignment_notifications(cls, assignment):
        cls.notify_rider(assignment)
        cls.notify_customer(assignment)
        cls.notify_vendor(assignment)