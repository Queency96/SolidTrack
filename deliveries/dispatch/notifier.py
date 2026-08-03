from deliveries.services import NotificationService


class DispatchNotifier:
    """
    Dispatch domain notification gateway.

    Responsible only for describing dispatch events.
    NotificationService decides which communication
    channels are used.
    """

    # ==================================================
    # Delivery Offer
    # ==================================================

    @classmethod
    def offer_delivery(
        cls,
        offer,
    ):
        cls._notify(
            user=offer.rider,
            title="New Delivery Request",
            message=(
                "You have a new delivery request "
                "waiting for your response."
            ),
            notification_type="DELIVERY_OFFER",
            data={
                "offer_id": offer.id,
                "delivery_id": offer.delivery.id,
            },
            send_push=True,
            send_sms=True,
        )

    # ==================================================
    # Rider Assigned
    # ==================================================

    @classmethod
    def notify_rider(
        cls,
        assignment,
    ):
        cls._notify(
            user=assignment.rider,
            title="Delivery Assigned",
            message=(
                "A delivery has been assigned to you."
            ),
            notification_type="DELIVERY",
            data={
                "assignment_id": assignment.id,
                "delivery_id": assignment.delivery.id,
            },
            send_push=True,
            send_sms=True,
        )

    # ==================================================
    # Customer Notification
    # ==================================================

    @classmethod
    def notify_customer(
        cls,
        assignment,
    ):
        rider = assignment.rider

        cls._notify(
            user=assignment.delivery.customer,
            title="Rider Assigned",
            message=(
                f"{rider.get_full_name()} "
                "has accepted your delivery request."
            ),
            notification_type="DELIVERY",
            data={
                "assignment_id": assignment.id,
                "delivery_id": assignment.delivery.id,
                "rider_id": rider.id,
            },
            send_email=True,
            send_push=True,
        )

    # ==================================================
    # Vendor Notification
    # ==================================================

    @classmethod
    def notify_vendor(
        cls,
        assignment,
    ):
        vendor = getattr(
            assignment.delivery,
            "vendor",
            None,
        )

        if not vendor:
            return

        cls._notify(
            user=vendor.user,
            title="Rider Assigned",
            message=(
                "A rider has been assigned "
                "for pickup."
            ),
            notification_type="DELIVERY",
            data={
                "assignment_id": assignment.id,
                "delivery_id": assignment.delivery.id,
            },
            send_push=True,
            send_email=True,
        )

    # ==================================================
    # Offer Rejected
    # ==================================================

    @classmethod
    def notify_offer_rejected(
        cls,
        offer,
    ):
        cls._notify(
            user=offer.rider,
            title="Delivery Rejected",
            message=(
                "You rejected this delivery request."
            ),
            notification_type="DELIVERY_OFFER",
            data={
                "offer_id": offer.id,
                "delivery_id": offer.delivery.id,
            },
            send_push=True,
        )

    # ==================================================
    # Offer Expired
    # ==================================================

    @classmethod
    def notify_offer_expired(
        cls,
        offer,
    ):
        cls._notify(
            user=offer.rider,
            title="Delivery Offer Expired",
            message=(
                "This delivery offer expired before "
                "a response was received."
            ),
            notification_type="DELIVERY_OFFER",
            data={
                "offer_id": offer.id,
                "delivery_id": offer.delivery.id,
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
    ):
        cls._notify(
            user=delivery.customer,
            title="Finding a Rider",
            message=(
                "We're currently unable to assign a rider. "
                "We'll continue searching automatically."
            ),
            notification_type="DELIVERY",
            data={
                "delivery_id": delivery.id,
            },
            send_email=True,
            send_push=True,
        )

    # ==================================================
    # Dispatch Cancelled
    # ==================================================

    @classmethod
    def notify_dispatch_cancelled(
        cls,
        delivery,
    ):
        cls._notify(
            user=delivery.customer,
            title="Dispatch Cancelled",
            message=(
                "The dispatch process for your delivery "
                "has been cancelled."
            ),
            notification_type="DELIVERY",
            data={
                "delivery_id": delivery.id,
            },
            send_email=True,
            send_push=True,
        )

    # ==================================================
    # Internal Helper
    # ==================================================

    @staticmethod
    def _notify(
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