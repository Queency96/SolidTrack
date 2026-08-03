from django.db import models


class DispatchStatus(models.TextChoices):
    """
    Lifecycle of a dispatch operation.
    """

    # ------------------------------------------
    # Initialization
    # ------------------------------------------

    CREATED = (
        "CREATED",
        "Created",
    )

    DISPATCHING = (
        "DISPATCHING",
        "Dispatching",
    )

    # ------------------------------------------
    # Rider Search
    # ------------------------------------------

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

    # ------------------------------------------
    # Delivery Offer
    # ------------------------------------------

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

    ACCEPTED = (
        "ACCEPTED",
        "Accepted",
    )

    REJECTED = (
        "REJECTED",
        "Rejected",
    )

    EXPIRED = (
        "EXPIRED",
        "Expired",
    )

    # ------------------------------------------
    # Assignment
    # ------------------------------------------

    ASSIGNING = (
        "ASSIGNING",
        "Assigning Rider",
    )

    ASSIGNED = (
        "ASSIGNED",
        "Assigned",
    )

    # ------------------------------------------
    # Completion
    # ------------------------------------------

    COMPLETED = (
        "COMPLETED",
        "Completed",
    )

    CANCELLED = (
        "CANCELLED",
        "Cancelled",
    )

    FAILED = (
        "FAILED",
        "Failed",
    )