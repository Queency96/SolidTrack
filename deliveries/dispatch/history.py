from deliveries.models.models import (
    DispatchHistory,
)


class DispatchHistoryService:
    """
    Writes immutable dispatch lifecycle events.

    All dispatch services should use this service instead
    of directly creating DispatchHistory records.
    """

    @classmethod
    def record(
        cls,
        *,
        delivery,
        event_type,
        message="",
        assignment=None,
        offer=None,
        rider=None,
        status="",
        reason="",
        metadata=None,
    ):
        if rider is None:
            if assignment is not None:
                rider = assignment.rider

            elif offer is not None:
                rider = offer.rider

        return DispatchHistory.objects.create(
            delivery=delivery,
            assignment=assignment,
            offer=offer,
            rider=rider,
            event_type=event_type,
            status=status or "",
            message=message,
            reason=reason,
            metadata=metadata or {},
        )

    # ==================================================
    # Delivery
    # ==================================================

    @classmethod
    def delivery_created(
        cls,
        delivery,
    ):
        return cls.record(
            delivery=delivery,
            event_type=(
                DispatchHistory.EventType
                .DELIVERY_CREATED
            ),
            message="Delivery created.",
            status=getattr(
                delivery,
                "status",
                "",
            ),
        )

    # ==================================================
    # Dispatch
    # ==================================================

    @classmethod
    def dispatch_started(
        cls,
        delivery,
    ):
        return cls.record(
            delivery=delivery,
            event_type=(
                DispatchHistory.EventType
                .DISPATCH_STARTED
            ),
            message="Dispatch process started.",
            status=getattr(
                delivery,
                "status",
                "",
            ),
        )

    # ==================================================
    # Offer
    # ==================================================

    @classmethod
    def offer_created(
        cls,
        offer,
    ):
        return cls.record(
            delivery=offer.delivery,
            offer=offer,
            rider=offer.rider,
            event_type=(
                DispatchHistory.EventType
                .OFFER_CREATED
            ),
            message=(
                "Delivery offer sent to rider."
            ),
            status=offer.status,
            metadata={
                "offer_id": str(offer.id),
                "search_radius": str(
                    offer.search_radius
                ),
                "expires_at": (
                    offer.expires_at.isoformat()
                    if offer.expires_at
                    else None
                ),
            },
        )

    @classmethod
    def offer_accepted(
        cls,
        offer,
        assignment=None,
    ):
        return cls.record(
            delivery=offer.delivery,
            offer=offer,
            assignment=assignment,
            rider=offer.rider,
            event_type=(
                DispatchHistory.EventType
                .OFFER_ACCEPTED
            ),
            message=(
                "Rider accepted the delivery offer."
            ),
            status=offer.status,
        )

    @classmethod
    def offer_rejected(
        cls,
        offer,
        reason="",
    ):
        return cls.record(
            delivery=offer.delivery,
            offer=offer,
            rider=offer.rider,
            event_type=(
                DispatchHistory.EventType
                .OFFER_REJECTED
            ),
            message=(
                "Rider rejected the delivery offer."
            ),
            status=offer.status,
            reason=reason,
        )

    @classmethod
    def offer_expired(
        cls,
        offer,
    ):
        return cls.record(
            delivery=offer.delivery,
            offer=offer,
            rider=offer.rider,
            event_type=(
                DispatchHistory.EventType
                .OFFER_EXPIRED
            ),
            message="Delivery offer expired.",
            status=offer.status,
        )

    @classmethod
    def offer_cancelled(
        cls,
        offer,
    ):
        return cls.record(
            delivery=offer.delivery,
            offer=offer,
            rider=offer.rider,
            event_type=(
                DispatchHistory.EventType
                .OFFER_CANCELLED
            ),
            message="Delivery offer cancelled.",
            status=offer.status,
        )

    # ==================================================
    # Assignment
    # ==================================================

    @classmethod
    def rider_assigned(
        cls,
        assignment,
    ):
        return cls.record(
            delivery=assignment.delivery,
            assignment=assignment,
            rider=assignment.rider,
            event_type=(
                DispatchHistory.EventType
                .RIDER_ASSIGNED
            ),
            message="Rider assigned to delivery.",
            status=assignment.status,
            metadata={
                "assignment_id": str(
                    assignment.id
                ),
            },
        )

    @classmethod
    def assignment_accepted(
        cls,
        assignment,
    ):
        return cls.record(
            delivery=assignment.delivery,
            assignment=assignment,
            rider=assignment.rider,
            event_type=(
                DispatchHistory.EventType
                .ASSIGNMENT_ACCEPTED
            ),
            message=(
                "Rider accepted the assignment."
            ),
            status=assignment.status,
        )

    @classmethod
    def assignment_cancelled(
        cls,
        assignment,
        reason="",
    ):
        return cls.record(
            delivery=assignment.delivery,
            assignment=assignment,
            rider=assignment.rider,
            event_type=(
                DispatchHistory.EventType
                .ASSIGNMENT_CANCELLED
            ),
            message="Assignment cancelled.",
            status=assignment.status,
            reason=reason,
        )

    @classmethod
    def assignment_reassigned(
        cls,
        assignment,
    ):
        return cls.record(
            delivery=assignment.delivery,
            assignment=assignment,
            rider=assignment.rider,
            event_type=(
                DispatchHistory.EventType
                .ASSIGNMENT_REASSIGNED
            ),
            message="Assignment reassigned.",
            status=assignment.status,
        )

    # ==================================================
    # Pickup / Delivery
    # ==================================================

    @classmethod
    def pickup_started(
        cls,
        assignment,
    ):
        return cls.record(
            delivery=assignment.delivery,
            assignment=assignment,
            rider=assignment.rider,
            event_type=(
                DispatchHistory.EventType
                .PICKUP_STARTED
            ),
            message="Rider started pickup.",
            status=assignment.status,
        )

    @classmethod
    def arrived_pickup(
        cls,
        assignment,
    ):
        return cls.record(
            delivery=assignment.delivery,
            assignment=assignment,
            rider=assignment.rider,
            event_type=(
                DispatchHistory.EventType
                .ARRIVED_PICKUP
            ),
            message="Rider arrived at pickup.",
            status=assignment.status,
        )

    @classmethod
    def pickup_completed(
        cls,
        assignment,
    ):
        return cls.record(
            delivery=assignment.delivery,
            assignment=assignment,
            rider=assignment.rider,
            event_type=(
                DispatchHistory.EventType
                .PICKUP_COMPLETED
            ),
            message="Package picked up.",
            status=assignment.status,
        )

    @classmethod
    def delivery_started(
        cls,
        assignment,
    ):
        return cls.record(
            delivery=assignment.delivery,
            assignment=assignment,
            rider=assignment.rider,
            event_type=(
                DispatchHistory.EventType
                .DELIVERY_STARTED
            ),
            message="Delivery started.",
            status=assignment.status,
        )

    @classmethod
    def arrived_destination(
        cls,
        assignment,
    ):
        return cls.record(
            delivery=assignment.delivery,
            assignment=assignment,
            rider=assignment.rider,
            event_type=(
                DispatchHistory.EventType
                .ARRIVED_DESTINATION
            ),
            message="Rider arrived at destination.",
            status=assignment.status,
        )

    @classmethod
    def delivery_completed(
        cls,
        assignment,
    ):
        return cls.record(
            delivery=assignment.delivery,
            assignment=assignment,
            rider=assignment.rider,
            event_type=(
                DispatchHistory.EventType
                .DELIVERY_COMPLETED
            ),
            message="Delivery completed.",
            status=assignment.status,
        )

    # ==================================================
    # Failure
    # ==================================================

    @classmethod
    def dispatch_failed(
        cls,
        delivery,
        reason="",
    ):
        return cls.record(
            delivery=delivery,
            event_type=(
                DispatchHistory.EventType
                .DISPATCH_FAILED
            ),
            message="Dispatch failed.",
            status=getattr(
                delivery,
                "status",
                "",
            ),
            reason=reason,
        )