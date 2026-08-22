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
    delivering the notification through the configured
    channels.

    This class does NOT:
    • Create notifications directly.
    • Send FCM requests directly.
    • Send emails directly.
    • Send SMS directly.
    """

    # ==================================================
    # Delivery Offer
    # ==================================================

    @classmethod
    def offer_delivery(
        cls,
        offer,
    ):
        """
        Notify a rider that a new delivery offer
        is available.
        """

        cls._notify(
            user=offer.rider,
            title="New Delivery Request",
            message=(
                "You have a new delivery request "
                "waiting for your response."
            ),
            notification_type="DELIVERY_OFFER",
            data={
                "offer_id": str(offer.id),
                "delivery_id": str(
                    offer.delivery.id
                ),
                "expires_at": (
                    offer.expires_at.isoformat()
                    if offer.expires_at
                    else None
                ),
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
        """
        Notify the rider that the delivery has
        been assigned.
        """

        cls._notify(
            user=assignment.rider,
            title="Delivery Assigned",
            message=(
                "A delivery has been assigned to you."
            ),
            notification_type="DELIVERY",
            data={
                "assignment_id": str(
                    assignment.id
                ),
                "delivery_id": str(
                    assignment.delivery.id
                ),
            },
            send_push=True,
            send_sms=True,
        )

    # ==================================================
    # Customer - Rider Assigned
    # ==================================================

    @classmethod
    def notify_customer(
        cls,
        assignment,
    ):
        """
        Notify the customer that a rider has
        accepted their delivery.
        """

        delivery = assignment.delivery
        rider = assignment.rider
        customer = getattr(
            delivery,
            "customer",
            None,
        )

        if customer is None:
            return

        rider_name = (
            rider.get_full_name()
            or getattr(
                rider,
                "email",
                "Your rider",
            )
        )

        cls._notify(
            user=customer,
            title="Rider Assigned",
            message=(
                f"{rider_name} has accepted "
                "your delivery request."
            ),
            notification_type="DELIVERY",
            data={
                "assignment_id": str(
                    assignment.id
                ),
                "delivery_id": str(
                    delivery.id
                ),
                "rider_id": str(
                    rider.id
                ),
            },
            send_email=True,
            send_push=True,
        )

    # ==================================================
    # Vendor - Rider Assigned
    # ==================================================

    @classmethod
    def notify_vendor(
        cls,
        assignment,
    ):
        """
        Notify the vendor that a rider has been
        assigned for pickup.
        """

        delivery = assignment.delivery

        vendor = getattr(
            delivery,
            "vendor",
            None,
        )

        if vendor is None:
            return

        vendor_user = getattr(
            vendor,
            "user",
            None,
        )

        if vendor_user is None:
            return

        cls._notify(
            user=vendor_user,
            title="Rider Assigned",
            message=(
                "A rider has been assigned "
                "for pickup."
            ),
            notification_type="DELIVERY",
            data={
                "assignment_id": str(
                    assignment.id
                ),
                "delivery_id": str(
                    delivery.id
                ),
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
        """
        Notify the rider that the offer was rejected.

        This can be useful for audit/confirmation,
        although it is optional because the rider
        initiated the rejection.
        """

        cls._notify(
            user=offer.rider,
            title="Delivery Rejected",
            message=(
                "You rejected this delivery request."
            ),
            notification_type="DELIVERY_OFFER",
            data={
                "offer_id": str(
                    offer.id
                ),
                "delivery_id": str(
                    offer.delivery.id
                ),
                "rejection_reason": (
                    offer.rejection_reason
                    or ""
                ),
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
        """
        Notify the rider that the delivery offer
        expired.
        """

        cls._notify(
            user=offer.rider,
            title="Delivery Offer Expired",
            message=(
                "This delivery offer expired before "
                "a response was received."
            ),
            notification_type="DELIVERY_OFFER",
            data={
                "offer_id": str(
                    offer.id
                ),
                "delivery_id": str(
                    offer.delivery.id
                ),
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
        """
        Notify the customer when dispatch currently
        cannot find an eligible rider.

        The delivery may still be retried automatically.
        """

        customer = getattr(
            delivery,
            "customer",
            None,
        )

        if customer is None:
            return

        cls._notify(
            user=customer,
            title="Finding a Rider",
            message=(
                "We're currently unable to assign "
                "a rider. We'll continue searching "
                "automatically."
            ),
            notification_type="DELIVERY",
            data={
                "delivery_id": str(
                    delivery.id
                ),
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
        """
        Notify the customer that dispatch has
        been cancelled.
        """

        customer = getattr(
            delivery,
            "customer",
            None,
        )

        if customer is None:
            return

        cls._notify(
            user=customer,
            title="Dispatch Cancelled",
            message=(
                "The dispatch process for your "
                "delivery has been cancelled."
            ),
            notification_type="DELIVERY",
            data={
                "delivery_id": str(
                    delivery.id
                ),
            },
            send_email=True,
            send_push=True,
        )

    # ==================================================
    # Redispatch Started
    # ==================================================

    @classmethod
    def notify_redispatch(
        cls,
        delivery,
    ):
        """
        Notify the customer that the system is
        searching for another rider.
        """

        customer = getattr(
            delivery,
            "customer",
            None,
        )

        if customer is None:
            return

        cls._notify(
            user=customer,
            title="Finding Another Rider",
            message=(
                "We're looking for another rider "
                "for your delivery."
            ),
            notification_type="DELIVERY",
            data={
                "delivery_id": str(
                    delivery.id
                ),
            },
            send_push=True,
        )

    # ==================================================
    # Internal Notification Gateway
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
        """
        Forward a notification request to the
        application's NotificationService.

        DispatchNotifier intentionally does not know
        how email, SMS, or push notifications are sent.
        """

        if user is None:
            return

        from deliveries.services import (
            NotificationService,
        )

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