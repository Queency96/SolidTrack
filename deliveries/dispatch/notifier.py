from django.db import transaction


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
    def offer_delivery(
        cls,
        offer,
    ):
        """
        Notify a rider that a new delivery offer
        is available.

        The offer must already exist in the database
        before this method is called.
        """

        if offer is None:
            return

        rider = getattr(
            offer,
            "rider",
            None,
        )

        delivery = getattr(
            offer,
            "delivery",
            None,
        )

        if rider is None or delivery is None:
            return

        expires_at = getattr(
            offer,
            "expires_at",
            None,
        )

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
                "delivery_id": str(
                    delivery.id
                ),
                "expires_at": (
                    expires_at.isoformat()
                    if expires_at
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

        This notification should normally be triggered
        after the assignment transaction commits.
        """

        if assignment is None:
            return

        rider = getattr(
            assignment,
            "rider",
            None,
        )

        delivery = getattr(
            assignment,
            "delivery",
            None,
        )

        if rider is None or delivery is None:
            return

        cls._safe_notify(
            user=rider,
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
                    delivery.id
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
        Notify the customer that a rider has been
        assigned to their delivery.
        """

        if assignment is None:
            return

        delivery = getattr(
            assignment,
            "delivery",
            None,
        )

        rider = getattr(
            assignment,
            "rider",
            None,
        )

        if delivery is None or rider is None:
            return

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
                None,
            )
            or "Your rider"
        )

        cls._safe_notify(
            user=customer,
            title="Rider Assigned",
            message=(
                f"{rider_name} has been assigned "
                "to your delivery."
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

        if assignment is None:
            return

        delivery = getattr(
            assignment,
            "delivery",
            None,
        )

        if delivery is None:
            return

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

        cls._safe_notify(
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
        Notify internal/customer-facing systems that
        an offer was rejected.

        By default, the rider is NOT notified because
        the rider initiated the rejection.

        This method is retained as a domain hook for
        future notification behavior.
        """

        if offer is None:
            return

        delivery = getattr(
            offer,
            "delivery",
            None,
        )

        if delivery is None:
            return

        # ----------------------------------------------
        # Optional customer notification
        # ----------------------------------------------
        #
        # We intentionally do not notify the rider here.
        # The rider already knows they rejected the offer.
        #
        # Customer notification can be enabled later if
        # product requirements call for it.

        return

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

        if offer is None:
            return

        rider = getattr(
            offer,
            "rider",
            None,
        )

        delivery = getattr(
            offer,
            "delivery",
            None,
        )

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
                "offer_id": str(
                    offer.id
                ),
                "delivery_id": str(
                    delivery.id
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

        if delivery is None:
            return

        customer = getattr(
            delivery,
            "customer",
            None,
        )

        if customer is None:
            return

        cls._safe_notify(
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

        if delivery is None:
            return

        customer = getattr(
            delivery,
            "customer",
            None,
        )

        if customer is None:
            return

        cls._safe_notify(
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

        if delivery is None:
            return

        customer = getattr(
            delivery,
            "customer",
            None,
        )

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

    # ==================================================
    # Safe Notification
    # ==================================================

    @classmethod
    def _safe_notify(
        cls,
        **kwargs,
    ):
        """
        Execute a notification without allowing a
        notification-channel failure to break the
        dispatch workflow.

        Dispatch state is already persisted independently
        from notification delivery.
        """

        try:

            cls._notify(
                **kwargs,
            )

        except Exception:
            # Notification failures must not invalidate
            # a successful dispatch/assignment operation.
            #
            # The application's notification subsystem
            # should perform its own logging/monitoring.
            return

    # ==================================================
    # Assignment Notifications
    # ==================================================

    @classmethod
    def schedule_assignment_notifications(
        cls,
        assignment,
    ):
        """
        Schedule assignment notifications to execute
        only after the surrounding database transaction
        successfully commits.

        This prevents users from receiving an assignment
        notification for an assignment that was later
        rolled back.
        """

        if assignment is None:
            return

        transaction.on_commit(
            lambda: cls._send_assignment_notifications(
                assignment,
            )
        )

    @classmethod
    def _send_assignment_notifications(
        cls,
        assignment,
    ):
        """
        Send all notifications related to a successful
        assignment.
        """

        cls.notify_rider(
            assignment,
        )

        cls.notify_customer(
            assignment,
        )

        cls.notify_vendor(
            assignment,
        )