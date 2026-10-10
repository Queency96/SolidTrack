"""
Customer-facing delivery timeline.

Two responsibilities:

    1. get_timeline(delivery)  — read the customer-facing
       timeline for a delivery.
    2. log(...)                — write a timeline entry
       AND its corresponding audit entry.

Writes are split as follows:

    DeliveryTimeline       — customer-facing entry (this file)
    DispatchHistory        — internal audit entry (delegated to
                             DispatchHistoryService)

DispatchHistoryService remains the sole writer for
DispatchHistory. This service delegates to its domain
methods (rider_assigned, offer_rejected, etc.) so no audit
logic is duplicated.
"""

import logging

from deliveries.models.delivery_timeline import (
    DeliveryTimeline,
)
from deliveries.models.dispatch_history import (
    DispatchHistory,
)
from deliveries.dispatch.history import (
    DispatchHistoryService,
)


logger = logging.getLogger(__name__)


class DeliveryTimelineService:
    """
    Customer-facing timeline reader and writer.

    The reader serializes DispatchHistory rows. The writer
    creates paired rows in DeliveryTimeline and
    DispatchHistory.
    """

    # ==================================================
    # Write
    # ==================================================

    @classmethod
    def log(
        cls,
        *,
        delivery,
        event,
        title,
        description="",
        rider=None,
        assignment=None,
        offer=None,
        reason="",
        metadata=None,
        created_by=None,
        write_history=True,
    ):
        """
        Write a delivery timeline entry.

        Parameters
        ----------
        delivery:
            The Delivery the entry belongs to.

        event:
            One of DeliveryTimeline.EventType.

        title:
            Short human-readable title.

        description:
            Optional longer text.

        rider, assignment, offer:
            Optional references, populated when the event
            relates to them. At least one of them is normally
            provided so the audit row carries the right
            subject.

        reason:
            Free-text reason, used for rejections and
            cancellations.

        metadata:
            Free-form JSON.

        created_by:
            Optional User who triggered the event (for
            admin-triggered timeline entries).

        write_history:
            When True (default), also write the corresponding
            DispatchHistory row via DispatchHistoryService.
            Set to False for timeline-only entries.
        """

        # --------------------------------------------------
        # Write the customer-facing row.
        # --------------------------------------------------

        timeline_entry = DeliveryTimeline.objects.create(
            delivery=delivery,
            rider=rider,
            event=event,
            title=title,
            description=description or "",
            metadata=metadata or {},
            created_by=created_by,
        )

        # --------------------------------------------------
        # Write the audit row.
        # --------------------------------------------------

        if write_history:

            try:
                cls._write_history_entry(
                    delivery=delivery,
                    event=event,
                    title=title,
                    description=description,
                    rider=rider,
                    assignment=assignment,
                    offer=offer,
                    reason=reason,
                    metadata=metadata,
                )
            except Exception:
                logger.exception(
                    "Failed to write DispatchHistory row for "
                    "timeline event %s on delivery %s.",
                    event,
                    getattr(delivery, "pk", None),
                )

        return timeline_entry

    # ==================================================
    # History delegation
    # ==================================================

    @classmethod
    def _write_history_entry(
        cls,
        *,
        delivery,
        event,
        title,
        description,
        rider,
        assignment,
        offer,
        reason,
        metadata,
    ):
        """
        Route a timeline event to its corresponding
        DispatchHistoryService domain method.

        The mapping is:

            CREATED          -> delivery_created(delivery)
            SEARCHING_RIDERS -> dispatch_started(delivery)
            OFFER_SENT       -> offer_created(offer)
            OFFER_ACCEPTED   -> offer_accepted(offer, assignment)
            OFFER_REJECTED   -> offer_rejected(offer, reason)
            OFFER_EXPIRED    -> offer_expired(offer)
            ASSIGNED         -> rider_assigned(assignment)
            RIDER_ARRIVED    -> arrived_pickup(assignment)
            PICKED_UP        -> pickup_completed(assignment)
            IN_TRANSIT       -> delivery_started(assignment)
            DELIVERED        -> delivery_completed(assignment)
            CANCELLED        -> assignment_cancelled(assignment, reason)
        """

        EventType = DeliveryTimeline.EventType

        # --------------------------------------------------
        # Delivery-scoped events
        # --------------------------------------------------

        if event == EventType.CREATED:
            DispatchHistoryService.delivery_created(delivery)
            return

        if event == EventType.SEARCHING_RIDERS:
            DispatchHistoryService.dispatch_started(delivery)
            return

        # --------------------------------------------------
        # Offer-scoped events
        # --------------------------------------------------

        if event == EventType.OFFER_SENT:

            if offer is None:
                logger.warning(
                    "OFFER_SENT timeline event with no offer; "
                    "skipping history write."
                )
                return

            DispatchHistoryService.offer_created(offer)
            return

        if event == EventType.OFFER_ACCEPTED:

            if offer is None:
                logger.warning(
                    "OFFER_ACCEPTED timeline event with no "
                    "offer; skipping history write."
                )
                return

            DispatchHistoryService.offer_accepted(
                offer,
                assignment=assignment,
            )
            return

        if event == EventType.OFFER_REJECTED:

            if offer is None:
                logger.warning(
                    "OFFER_REJECTED timeline event with no "
                    "offer; skipping history write."
                )
                return

            DispatchHistoryService.offer_rejected(
                offer,
                reason=reason or "",
            )
            return

        if event == EventType.OFFER_EXPIRED:

            if offer is None:
                logger.warning(
                    "OFFER_EXPIRED timeline event with no "
                    "offer; skipping history write."
                )
                return

            DispatchHistoryService.offer_expired(offer)
            return

        # --------------------------------------------------
        # Assignment-scoped events
        # --------------------------------------------------

        if assignment is None:
            logger.warning(
                "Timeline event %s requires an assignment; "
                "skipping history write.",
                event,
            )
            return

        if event == EventType.ASSIGNED:
            DispatchHistoryService.rider_assigned(assignment)
            return

        if event == EventType.RIDER_ARRIVED:
            DispatchHistoryService.arrived_pickup(assignment)
            return

        if event == EventType.PICKED_UP:
            DispatchHistoryService.pickup_completed(assignment)
            return

        if event == EventType.IN_TRANSIT:
            DispatchHistoryService.delivery_started(assignment)
            return

        if event == EventType.DELIVERED:
            DispatchHistoryService.delivery_completed(assignment)
            return

        if event == EventType.CANCELLED:
            DispatchHistoryService.assignment_cancelled(
                assignment,
                reason=reason or "",
            )
            return

        # --------------------------------------------------
        # Unknown
        # --------------------------------------------------

        logger.warning(
            "No DispatchHistoryService mapping for timeline "
            "event %s.",
            event,
        )

    # ==================================================
    # Read
    # ==================================================

    @classmethod
    def get_timeline(
        cls,
        delivery,
    ):
        """
        Return the customer-facing timeline for a delivery.

        Reads from DispatchHistory (the audit trail).
        """

        history = (
            DispatchHistory.objects
            .filter(delivery=delivery)
            .select_related(
                "rider",
                "offer",
                "assignment",
            )
            .order_by("created_at")
        )

        return [
            cls._serialize_event(event)
            for event in history
        ]

    # ==================================================
    # Serialize
    # ==================================================

    @staticmethod
    def _serialize_event(event):

        return {
            "id": event.id,
            "event_type": event.event_type,
            "status": event.status,
            "message": event.message,
            "reason": event.reason,
            "timestamp": event.created_at,

            "delivery_id": event.delivery_id,
            "offer_id": event.offer_id,
            "assignment_id": event.assignment_id,
            "rider_id": event.rider_id,

            "metadata": event.metadata,
        }