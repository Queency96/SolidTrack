"""
Event listeners for the dispatch publisher.

Three concerns:

    1. Customer and vendor notifications when a rider is
       assigned.
    2. Rider notification when an offer is rejected.
    3. Timeline + audit logging for assignment, rejection,
       and expiration events.
"""

from .notifier import DispatchNotifier
from .timeline import DeliveryTimelineService
from deliveries.models.delivery_timeline import (
    DeliveryTimeline,
)


# ==================================================
# Assignment succeeded
# ==================================================

def notify_customer_offer_accepted(event):
    """Notify the customer that a rider was assigned."""
    DispatchNotifier.notify_customer(event.assignment)


def notify_vendor_offer_accepted(event):
    """Notify the vendor that a rider was assigned."""
    DispatchNotifier.notify_vendor(event.assignment)


def log_offer_accepted(event):
    """
    Write a RIDER_ASSIGNED timeline entry plus its
    corresponding audit row.
    """
    assignment = event.assignment

    DeliveryTimelineService.log(
        delivery=assignment.delivery,
        rider=assignment.rider,
        assignment=assignment,
        event=DeliveryTimeline.EventType.ASSIGNED,
        title="Rider Assigned",
        description="Delivery accepted by rider.",
    )


# ==================================================
# Offer rejected
# ==================================================

def notify_rider_offer_rejected(event):
    """Notify the rider that their offer was recorded as rejected."""
    DispatchNotifier.notify_offer_rejected(event.offer)


def log_offer_rejected(event):
    """
    Write an OFFER_REJECTED timeline entry plus its
    corresponding audit row.
    """
    offer = event.offer

    DeliveryTimelineService.log(
        delivery=offer.delivery,
        rider=offer.rider,
        offer=offer,
        event=DeliveryTimeline.EventType.OFFER_REJECTED,
        title="Offer Rejected",
        description="Rider rejected delivery.",
        reason=getattr(offer, "rejection_reason", "") or "",
    )


# ==================================================
# Offer expired
# ==================================================

def log_offer_expired(event):
    """
    Write an OFFER_EXPIRED timeline entry plus its
    corresponding audit row.
    """
    offer = event.offer

    DeliveryTimelineService.log(
        delivery=offer.delivery,
        rider=offer.rider,
        offer=offer,
        event=DeliveryTimeline.EventType.OFFER_EXPIRED,
        title="Offer Expired",
        description="Delivery offer expired without a response.",
    )