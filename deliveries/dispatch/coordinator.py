from django.db import transaction

from deliveries.constants import DeliveryOfferAction
from deliveries.models import (
    Delivery,
    DeliveryOffer,
)

from .assignment import AssignmentService
from .context import DispatchContext
from .events import (
    DeliveryCreatedEvent,
    DeliveryOfferAcceptedEvent,
    DeliveryOfferExpiredEvent,
    DeliveryOfferRejectedEvent,
)
from .exceptions import (
    AssignmentAlreadyExists,
    DispatchConfigurationError,
    InvalidOfferState,
    NoAvailableRider,
)
from .notifier import DispatchNotifier
from .offer import DeliveryOfferService
from .pipeline import DispatchPipeline
from .publisher import EventPublisher
from .result import DispatchResult
from .service import DispatchConfigurationService
from .status import DispatchStatus


class DispatchCoordinator:
    """
    Central coordinator for the complete dispatch lifecycle.

    Responsibilities
    ----------------
    • Handle delivery-created events
    • Start dispatch
    • Create dispatch context
    • Process rider offer responses
    • Accept offers
    • Reject offers
    • Expire offers
    • Cancel offers
    • Create assignments
    • Redispatch deliveries
    • Track previously attempted riders
    • Publish dispatch events
    • Trigger dispatch failure notifications
    • Return standardized DispatchResult objects

    The coordinator orchestrates the dispatch workflow.

    It does NOT contain:
        • Rider eligibility logic
        • Distance calculation
        • Rider scoring
        • Offer state logic
        • Assignment state logic
    """

    # ==================================================
    # Delivery Created
    # ==================================================

    @classmethod
    def delivery_created(
        cls,
        delivery,
    ):
        """
        Called after a delivery has been successfully
        created.

        Publishes the delivery-created event and starts
        the dispatch process.
        """

        EventPublisher.publish(
            DeliveryCreatedEvent(
                delivery=delivery,
            )
        )

        return cls.dispatch(
            delivery=delivery,
        )

    # ==================================================
    # Dispatch
    # ==================================================

    @classmethod
    def dispatch(
        cls,
        delivery,
        excluded_rider_ids=None,
        attempt=None,
    ):
        """
        Start or restart dispatch for a delivery.

        A fresh DispatchContext is created for every
        dispatch invocation.

        Persistent DeliveryOffer history is used to
        determine riders that have already received
        offers.

        Explicit exclusions are merged with persistent
        exclusions.
        """

        try:

            # ------------------------------------------
            # Validate delivery
            # ------------------------------------------

            if delivery is None:
                return DispatchResult.failure_result(
                    status=DispatchStatus.FAILED,
                    message=(
                        "Delivery is required "
                        "for dispatch."
                    ),
                    errors=[
                        "Delivery cannot be None.",
                    ],
                )

            # ------------------------------------------
            # Terminal delivery check
            # ------------------------------------------

            if cls._delivery_is_terminal(
                delivery,
            ):
                return DispatchResult.failure_result(
                    status=DispatchStatus.FAILED,
                    message=(
                        "Delivery is no longer "
                        "eligible for dispatch."
                    ),
                    delivery=delivery,
                )

            # ------------------------------------------
            # Load configuration
            # ------------------------------------------

            config = (
                DispatchConfigurationService
                .get_configuration()
            )

            # ------------------------------------------
            # Determine attempt
            # ------------------------------------------

            if attempt is None:
                attempt = cls._get_current_attempt(
                    delivery,
                )

            # ------------------------------------------
            # Validate attempt limit
            # ------------------------------------------

            if cls._attempt_limit_reached(
                config=config,
                attempt=attempt,
            ):
                return cls._dispatch_failure(
                    delivery=delivery,
                    message=(
                        "Maximum dispatch assignment "
                        "attempts have been reached."
                    ),
                    errors=[
                        "Dispatch attempt limit reached.",
                    ],
                )

            # ------------------------------------------
            # Create context
            # ------------------------------------------

            context = DispatchContext(
                delivery=delivery,
                config=config,
                customer=getattr(
                    delivery,
                    "customer",
                    None,
                ),
                vendor=getattr(
                    delivery,
                    "vendor",
                    None,
                ),
                attempt=attempt,
            )

            # ------------------------------------------
            # Persistent exclusions
            # ------------------------------------------

            persistent_exclusions = (
                cls._get_excluded_rider_ids(
                    delivery=delivery,
                )
            )

            # ------------------------------------------
            # Merge explicit exclusions
            # ------------------------------------------

            if excluded_rider_ids:

                persistent_exclusions.update(
                    excluded_rider_ids,
                )

            # ------------------------------------------
            # Store exclusions in context
            # ------------------------------------------

            if persistent_exclusions:

                context.exclude_riders(
                    persistent_exclusions,
                )

            # ------------------------------------------
            # Execute pipeline
            # ------------------------------------------

            pipeline = DispatchPipeline(
                context=context,
            )

            result = pipeline.run()

            # ------------------------------------------
            # Dispatch failure notification
            # ------------------------------------------

            if (
                result.status
                == DispatchStatus.FAILED
            ):
                DispatchNotifier.notify_dispatch_failed(
                    delivery,
                )

            return result

        except DispatchConfigurationError as exc:

            return cls._dispatch_failure(
                delivery=delivery,
                message=str(exc),
                errors=[str(exc)],
            )

        except NoAvailableRider as exc:

            return cls._dispatch_failure(
                delivery=delivery,
                message=str(exc),
                errors=[str(exc)],
            )

        except Exception as exc:

            return cls._dispatch_failure(
                delivery=delivery,
                message=(
                    "An unexpected error occurred "
                    "during dispatch."
                ),
                errors=[str(exc)],
            )

    # ==================================================
    # Dispatch Failure
    # ==================================================

    @classmethod
    def _dispatch_failure(
        cls,
        delivery,
        message,
        errors=None,
    ):
        """
        Standardize dispatch failure handling.
        """

        if delivery is not None:

            try:
                DispatchNotifier.notify_dispatch_failed(
                    delivery,
                )
            except Exception:
                pass

        return DispatchResult.failure_result(
            status=DispatchStatus.FAILED,
            message=message,
            delivery=delivery,
            errors=errors or [],
        )

    # ==================================================
    # Rider Response
    # ==================================================

    @classmethod
    def respond_to_offer(
        cls,
        offer,
        action,
        reason="",
    ):
        """
        Process a rider's response to a delivery offer.
        """

        if offer is None:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message="Delivery offer is required.",
                errors=[
                    "Offer cannot be None.",
                ],
            )

        if action == DeliveryOfferAction.ACCEPT:

            return cls._accept_offer(
                offer=offer,
            )

        if action == DeliveryOfferAction.REJECT:

            return cls._reject_offer(
                offer=offer,
                reason=reason,
            )

        return DispatchResult.failure_result(
            status=DispatchStatus.FAILED,
            message="Invalid dispatch action.",
            delivery=offer.delivery,
            offer=offer,
            errors=[
                "Unsupported delivery offer action.",
            ],
        )

    # ==================================================
    # Accept Offer
    # ==================================================

    @classmethod
    def _accept_offer(
        cls,
        offer,
    ):
        """
        Accept an offer and create the corresponding
        rider assignment.

        Offer acceptance and assignment creation are
        performed atomically.
        """

        try:

            with transaction.atomic():

                # --------------------------------------
                # Accept offer
                # --------------------------------------

                accepted_offer = (
                    DeliveryOfferService.accept(
                        offer=offer,
                    )
                )

                # --------------------------------------
                # Create assignment
                # --------------------------------------

                assignment = (
                    AssignmentService.assign(
                        delivery=(
                            accepted_offer.delivery
                        ),
                        rider=(
                            accepted_offer.rider
                        ),
                    )
                )

                # --------------------------------------
                # Publish event
                # --------------------------------------

                EventPublisher.publish(
                    DeliveryOfferAcceptedEvent(
                        assignment=assignment,
                    )
                )

                # --------------------------------------
                # Return success
                # --------------------------------------

                return DispatchResult.success_result(
                    status=DispatchStatus.ACCEPTED,
                    message=(
                        "Delivery offer accepted "
                        "and rider assigned."
                    ),
                    delivery=(
                        accepted_offer.delivery
                    ),
                    assignment=assignment,
                    offer=accepted_offer,
                )

        except InvalidOfferState as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=str(exc),
                delivery=offer.delivery,
                offer=offer,
                errors=[str(exc)],
            )

        except AssignmentAlreadyExists as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.ASSIGNED,
                message=(
                    "Delivery has already been "
                    "assigned to a rider."
                ),
                delivery=offer.delivery,
                offer=offer,
                errors=[str(exc)],
            )

        except Exception as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=(
                    "Unable to accept "
                    "delivery offer."
                ),
                delivery=offer.delivery,
                offer=offer,
                errors=[str(exc)],
            )

    # ==================================================
    # Reject Offer
    # ==================================================

    @classmethod
    def _reject_offer(
        cls,
        offer,
        reason="",
    ):
        """
        Reject the current offer.

        If automatic redispatch is enabled, the delivery
        is immediately sent back through the dispatch
        pipeline.

        The rejected rider remains permanently excluded
        because the exclusion is derived from persistent
        DeliveryOffer history.
        """

        try:

            # ------------------------------------------
            # Reject offer
            # ------------------------------------------

            rejected_offer = (
                DeliveryOfferService.reject(
                    offer=offer,
                    reason=reason,
                )
            )

            # ------------------------------------------
            # Publish event
            # ------------------------------------------

            EventPublisher.publish(
                DeliveryOfferRejectedEvent(
                    offer=rejected_offer,
                )
            )

            # ------------------------------------------
            # Notify rider
            # ------------------------------------------

            DispatchNotifier.notify_offer_rejected(
                rejected_offer,
            )

            # ------------------------------------------
            # Load configuration
            # ------------------------------------------

            config = (
                DispatchConfigurationService
                .get_configuration()
            )

            # ------------------------------------------
            # Auto redispatch disabled
            # ------------------------------------------

            if not config.auto_redispatch:

                return DispatchResult.success_result(
                    status=DispatchStatus.REJECTED,
                    message=(
                        "Delivery offer rejected. "
                        "Automatic redispatch is disabled."
                    ),
                    delivery=rejected_offer.delivery,
                    offer=rejected_offer,
                )

            # ------------------------------------------
            # Redispatch
            # ------------------------------------------

            excluded_rider_ids = (
                cls._get_excluded_rider_ids(
                    delivery=rejected_offer.delivery,
                )
            )

            redispatch_result = cls.dispatch(
                delivery=rejected_offer.delivery,
                excluded_rider_ids=(
                    excluded_rider_ids
                ),
                attempt=cls._get_current_attempt(
                    rejected_offer.delivery,
                ),
            )

            # ------------------------------------------
            # Preserve rejection information
            # ------------------------------------------

            redispatch_result.offer = (
                rejected_offer
            )

            redispatch_result.add_warning(
                "Previous rider rejected the offer."
            )

            return redispatch_result

        except InvalidOfferState as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=str(exc),
                delivery=offer.delivery,
                offer=offer,
                errors=[str(exc)],
            )

    # ==================================================
    # Offer Expired
    # ==================================================

    @classmethod
    def offer_expired(
        cls,
        offer,
    ):
        """
        Expire an offer and redispatch the delivery.

        The expired rider remains excluded because
        persistent offer history records the previous
        attempt.
        """

        try:

            # ------------------------------------------
            # Expire offer
            # ------------------------------------------

            expired_offer = (
                DeliveryOfferService.expire(
                    offer=offer,
                )
            )

            # ------------------------------------------
            # Publish event
            # ------------------------------------------

            EventPublisher.publish(
                DeliveryOfferExpiredEvent(
                    offer=expired_offer,
                )
            )

            # ------------------------------------------
            # Notify rider
            # ------------------------------------------

            DispatchNotifier.notify_offer_expired(
                expired_offer,
            )

            # ------------------------------------------
            # Load configuration
            # ------------------------------------------

            config = (
                DispatchConfigurationService
                .get_configuration()
            )

            # ------------------------------------------
            # Auto redispatch disabled
            # ------------------------------------------

            if not config.auto_redispatch:

                return DispatchResult.success_result(
                    status=DispatchStatus.EXPIRED,
                    message=(
                        "Delivery offer expired. "
                        "Automatic redispatch is disabled."
                    ),
                    delivery=expired_offer.delivery,
                    offer=expired_offer,
                )

            # ------------------------------------------
            # Redispatch
            # ------------------------------------------

            excluded_rider_ids = (
                cls._get_excluded_rider_ids(
                    delivery=expired_offer.delivery,
                )
            )

            redispatch_result = cls.dispatch(
                delivery=expired_offer.delivery,
                excluded_rider_ids=(
                    excluded_rider_ids
                ),
                attempt=cls._get_current_attempt(
                    expired_offer.delivery,
                ),
            )

            # ------------------------------------------
            # Preserve expiration information
            # ------------------------------------------

            redispatch_result.offer = (
                expired_offer
            )

            redispatch_result.add_warning(
                "Previous rider offer expired."
            )

            return redispatch_result

        except InvalidOfferState as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=str(exc),
                delivery=offer.delivery,
                offer=offer,
                errors=[str(exc)],
            )

    # ==================================================
    # Cancel Offer
    # ==================================================

    @classmethod
    def cancel_offer(
        cls,
        offer,
    ):
        """
        Cancel a pending delivery offer.

        Cancellation does not automatically redispatch
        the delivery.
        """

        try:

            cancelled_offer = (
                DeliveryOfferService.cancel(
                    offer=offer,
                )
            )

            return DispatchResult.success_result(
                status=DispatchStatus.CANCELLED,
                message="Delivery offer cancelled.",
                delivery=(
                    cancelled_offer.delivery
                ),
                offer=cancelled_offer,
            )

        except InvalidOfferState as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=str(exc),
                delivery=offer.delivery,
                offer=offer,
                errors=[str(exc)],
            )

    # ==================================================
    # Persistent Exclusions
    # ==================================================

    @staticmethod
    def _get_excluded_rider_ids(
        delivery,
    ):
        """
        Return riders that have already received an
        offer for this delivery.

        DeliveryOffer is the persistent source of truth
        for rider attempt history.
        """

        return set(
            DeliveryOffer.objects
            .filter(
                delivery=delivery,
            )
            .values_list(
                "rider_id",
                flat=True,
            )
        )

    # ==================================================
    # Current Attempt
    # ==================================================

    @staticmethod
    def _get_current_attempt(
        delivery,
    ):
        """
        Determine the next dispatch attempt number.

        Every historical offer represents one rider
        dispatch attempt.
        """

        previous_attempts = (
            DeliveryOffer.objects
            .filter(
                delivery=delivery,
            )
            .count()
        )

        return previous_attempts + 1

    # ==================================================
    # Attempt Limit
    # ==================================================

    @staticmethod
    def _attempt_limit_reached(
        config,
        attempt,
    ):
        """
        Determine whether the configured maximum
        dispatch attempts has been reached.
        """

        maximum_attempts = (
            config.max_assignment_attempts
        )

        if maximum_attempts <= 0:
            return False

        return attempt > maximum_attempts

    # ==================================================
    # Delivery State
    # ==================================================

    @staticmethod
    def _delivery_is_terminal(
        delivery,
    ):
        """
        Determine whether dispatch should no longer run.

        DELIVERED and CANCELLED are terminal.

        FAILED remains retryable.
        """

        terminal_statuses = {
            Delivery.DeliveryStatus.DELIVERED,
            Delivery.DeliveryStatus.CANCELLED,
        }

        return (
            delivery.status
            in terminal_statuses
        )