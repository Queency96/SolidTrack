from django.db import models


class DispatchStatus(models.TextChoices):
    """
    Orchestration-level status of a dispatch operation.

    DispatchStatus does NOT replace:

        DeliveryOffer.Status

    or:

        DeliveryAssignment.AssignmentStatus

    Those models own their own persistent lifecycles.
    """

    # ==================================================
    # Initialization
    # ==================================================

    CREATED = (
        "CREATED",
        "Created",
    )

    # ==================================================
    # Dispatch
    # ==================================================

    DISPATCHING = (
        "DISPATCHING",
        "Dispatching",
    )

    # ==================================================
    # Rider Search
    # ==================================================

    SEARCHING = (
        "SEARCHING",
        "Searching Riders",
    )

    MATCHED = (
        "MATCHED",
        "Riders Found",
    )

    RANKED = (
        "RANKED",
        "Riders Ranked",
    )

    # ==================================================
    # Offer
    # ==================================================

    OFFER_CREATED = (
        "OFFER_CREATED",
        "Offer Created",
    )

    OFFERED = (
        "OFFERED",
        "Offer Sent",
    )

    WAITING = (
        "WAITING",
        "Waiting For Rider",
    )

    # ==================================================
    # Offer Response
    # ==================================================

    ACCEPTED = (
        "ACCEPTED",
        "Offer Accepted",
    )

    REJECTED = (
        "REJECTED",
        "Offer Rejected",
    )

    EXPIRED = (
        "EXPIRED",
        "Offer Expired",
    )

    # ==================================================
    # Assignment
    # ==================================================

    ASSIGNING = (
        "ASSIGNING",
        "Assigning Rider",
    )

    ASSIGNED = (
        "ASSIGNED",
        "Rider Assigned",
    )

    # ==================================================
    # Completion
    # ==================================================

    COMPLETED = (
        "COMPLETED",
        "Dispatch Completed",
    )

    # ==================================================
    # Cancellation / Failure
    # ==================================================

    CANCELLED = (
        "CANCELLED",
        "Dispatch Cancelled",
    )

    FAILED = (
        "FAILED",
        "Dispatch Failed",
    )