from django.db import transaction
from deliveries.constants import DeliveryOfferAction
from deliveries.models.delivery import Delivery
from deliveries.models.delivery_assignment import DeliveryAssignment
from deliveries.models.delivery_offer import DeliveryOffer
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
    • Create dispatch contexts
    • Process rider offer responses
    • Accept offers
    • Reject offers
    • Expire offers
    • Cancel offers
    • Create assignments
    • Redispatch deliveries
    • Track previously attempted riders
    • Enforce maximum rider-assignment attempts
    • Publish dispatch events
    • Trigger dispatch failure notifications
    • Return standardized DispatchResult objects

    Important
    ---------
    max_rider_assignments represents the maximum number of
    rider assignment attempts allowed for a delivery.

    A DeliveryOffer is NOT an assignment.

    Therefore:

        DeliveryOffer
            =
        Rider was offered the delivery

        DeliveryAssignment
            =
        Rider was actually assigned

    Rejected and expired offers do not themselves consume
    an assignment.

    However, each new rider can be attempted through the
    dispatch lifecycle until the configured maximum rider
    assignment limit is reached.

    Persistent rider-attempt history is derived from
    DeliveryOffer records.

    DispatchContext stores the in-memory state of the
    current dispatch attempt.

    The coordinator does NOT contain:

        • Rider eligibility logic
        • Distance calculation
        • Rider scoring
        • Ranking logic
        • Offer state-transition logic
        • Assignment business logic
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
        Handle a newly created delivery.

        The delivery-created event is published before
        dispatch begins.

        Dispatch itself starts from this coordinator.
        """

        if delivery is None:
            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message="Delivery is required for dispatch.",
                errors=[
                    "Delivery cannot be None.",
                ],
            )

        try:
            EventPublisher.publish(
                DeliveryCreatedEvent(
                    delivery=delivery,
                )
            )

        except Exception:
            # Event publication must never prevent dispatch.
            pass

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

        Every invocation creates a fresh DispatchContext.

        Persistent DeliveryOffer history is used to exclude
        riders that have already received an offer.

        Parameters
        ----------
        delivery:
            Delivery being dispatched.

        excluded_rider_ids:
            Optional rider IDs to exclude.

        attempt:
            Optional explicit dispatch attempt number.

        Returns
        -------
        DispatchResult
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
            # Terminal delivery validation
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
                    errors=[
                        "Delivery is in a terminal state.",
                    ],
                )

            # ------------------------------------------
            # Load configuration
            # ------------------------------------------

            config = (
                DispatchConfigurationService
                .get_configuration()
            )

            if config is None:
                raise DispatchConfigurationError(
                    "No active dispatch configuration "
                    "is available."
                )

            # ------------------------------------------
            # Determine dispatch attempt
            # ------------------------------------------

            if attempt is None:
                attempt = cls._get_current_attempt(
                    delivery,
                )

            # ------------------------------------------
            # Normalize attempt
            # ------------------------------------------

            try:
                attempt = int(attempt)

            except (
                TypeError,
                ValueError,
            ):
                raise DispatchConfigurationError(
                    "Dispatch attempt must be "
                    "a valid integer."
                )

            # ------------------------------------------
            # Validate attempt
            # ------------------------------------------

            if attempt <= 0:
                raise DispatchConfigurationError(
                    "Dispatch attempt must be "
                    "greater than zero."
                )

            # ------------------------------------------
            # Validate maximum rider assignments
            # ------------------------------------------

            if cls._maximum_rider_assignments_reached(
                delivery=delivery,
                config=config,
            ):
                return cls._dispatch_failure(
                    delivery=delivery,
                    message=(
                        "Maximum rider assignment "
                        "attempts have been reached."
                    ),
                    errors=[
                        "Maximum rider assignment limit reached.",
                    ],
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
            # Explicit exclusions
            # ------------------------------------------

            if excluded_rider_ids:
                persistent_exclusions.update(
                    excluded_rider_ids,
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
                store=getattr(
                    delivery,
                    "store",
                    None,
                ),
                attempt=attempt,
                excluded_rider_ids=(
                    persistent_exclusions
                ),
            )

            # ------------------------------------------
            # Metadata
            # ------------------------------------------

            context.add_metadata(
                "dispatch_attempt",
                attempt,
            )

            context.add_metadata(
                "persistent_excluded_rider_count",
                len(
                    persistent_exclusions,
                ),
            )

            context.add_metadata(
                "maximum_rider_assignments",
                cls._get_maximum_rider_assignments(
                    config,
                ),
            )

            context.add_metadata(
                "completed_rider_assignments",
                cls._get_completed_assignment_count(
                    delivery,
                ),
            )

            # ------------------------------------------
            # Execute pipeline
            # ------------------------------------------

            pipeline = DispatchPipeline(
                context=context,
            )

            result = pipeline.run()

            # ------------------------------------------
            # Pipeline failure
            # ------------------------------------------

            if result.status == DispatchStatus.FAILED:
                cls._notify_dispatch_failed(
                    delivery,
                )

            return result

        except DispatchConfigurationError as exc:

            return cls._dispatch_failure(
                delivery=delivery,
                message=str(exc),
                errors=[
                    str(exc),
                ],
            )

        except NoAvailableRider as exc:

            return cls._dispatch_failure(
                delivery=delivery,
                message=str(exc),
                errors=[
                    str(exc),
                ],
            )

        except Exception as exc:

            return cls._dispatch_failure(
                delivery=delivery,
                message=(
                    "An unexpected error occurred "
                    "during dispatch."
                ),
                errors=[
                    str(exc),
                ],
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

        Failure notification must never cause another
        exception.
        """

        if delivery is not None:
            cls._notify_dispatch_failed(
                delivery,
            )

        return DispatchResult.failure_result(
            status=DispatchStatus.FAILED,
            message=message,
            delivery=delivery,
            errors=errors or [],
        )

    # ==================================================
    # Failure Notification
    # ==================================================

    @staticmethod
    def _notify_dispatch_failed(
        delivery,
    ):
        """
        Safely notify that dispatch failed.

        Notification failure must never propagate.
        """

        try:
            DispatchNotifier.notify_dispatch_failed(
                delivery,
            )

        except Exception:
            pass

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

        Supported actions:

            ACCEPT
            REJECT
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

        Delivery is locked first.

        Offer acceptance and assignment creation occur
        within the same transaction.

        The actual assignment is created by
        AssignmentService.
        """

        if offer is None:
            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message="Delivery offer is required.",
                errors=[
                    "Offer cannot be None.",
                ],
            )

        try:

            with transaction.atomic():

                # --------------------------------------
                # Lock delivery
                # --------------------------------------

                delivery = (
                    Delivery.objects
                    .select_for_update()
                    .get(
                        pk=offer.delivery_id,
                    )
                )

                # --------------------------------------
                # Terminal validation
                # --------------------------------------

                if cls._delivery_is_terminal(
                    delivery,
                ):
                    raise InvalidOfferState(
                        "Cannot accept an offer for "
                        "a terminal delivery."
                    )

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
                        delivery=delivery,
                        rider=accepted_offer.rider,
                    )
                )

                # --------------------------------------
                # Publish event after commit
                # --------------------------------------

                transaction.on_commit(
                    lambda assignment=assignment: (
                        EventPublisher.publish(
                            DeliveryOfferAcceptedEvent(
                                assignment=assignment,
                            )
                        )
                    )
                )

                # --------------------------------------
                # Success
                # --------------------------------------

                return DispatchResult.success_result(
                    status=DispatchStatus.ACCEPTED,
                    message=(
                        "Delivery offer accepted "
                        "and rider assigned."
                    ),
                    delivery=delivery,
                    assignment=assignment,
                    offer=accepted_offer,
                )

        except InvalidOfferState as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=str(exc),
                delivery=offer.delivery,
                offer=offer,
                errors=[
                    str(exc),
                ],
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
                errors=[
                    str(exc),
                ],
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
                errors=[
                    str(exc),
                ],
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

        Rejection does not create an assignment.

        If automatic redispatch is enabled, another rider
        can be offered the delivery, provided the maximum
        rider-assignment limit has not been reached.
        """

        if offer is None:
            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message="Delivery offer is required.",
                errors=[
                    "Offer cannot be None.",
                ],
            )

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

            cls._publish_after_commit(
                DeliveryOfferRejectedEvent(
                    offer=rejected_offer,
                )
            )

            # ------------------------------------------
            # Notify
            # ------------------------------------------

            cls._notify_offer_rejected(
                rejected_offer,
            )

            # ------------------------------------------
            # Redispatch
            # ------------------------------------------

            return cls._redispatch_after_offer(
                offer=rejected_offer,
                status=DispatchStatus.REJECTED,
                warning=(
                    "Previous rider rejected "
                    "the offer."
                ),
            )

        except InvalidOfferState as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=str(exc),
                delivery=offer.delivery,
                offer=offer,
                errors=[
                    str(exc),
                ],
            )

        except DispatchConfigurationError as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=str(exc),
                delivery=offer.delivery,
                offer=offer,
                errors=[
                    str(exc),
                ],
            )

        except Exception as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=(
                    "Unable to process rejected "
                    "delivery offer."
                ),
                delivery=offer.delivery,
                offer=offer,
                errors=[
                    str(exc),
                ],
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
        Expire an offer and optionally redispatch.

        Expiration does not create an assignment.

        The expired rider remains excluded from future
        dispatch attempts.
        """

        if offer is None:
            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message="Delivery offer is required.",
                errors=[
                    "Offer cannot be None.",
                ],
            )

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

            cls._publish_after_commit(
                DeliveryOfferExpiredEvent(
                    offer=expired_offer,
                )
            )

            # ------------------------------------------
            # Notify
            # ------------------------------------------

            cls._notify_offer_expired(
                expired_offer,
            )

            # ------------------------------------------
            # Redispatch
            # ------------------------------------------

            return cls._redispatch_after_offer(
                offer=expired_offer,
                status=DispatchStatus.EXPIRED,
                warning=(
                    "Previous rider offer "
                    "expired."
                ),
            )

        except InvalidOfferState as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=str(exc),
                delivery=offer.delivery,
                offer=offer,
                errors=[
                    str(exc),
                ],
            )

        except DispatchConfigurationError as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=str(exc),
                delivery=offer.delivery,
                offer=offer,
                errors=[
                    str(exc),
                ],
            )

        except Exception as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=(
                    "Unable to process expired "
                    "delivery offer."
                ),
                delivery=offer.delivery,
                offer=offer,
                errors=[
                    str(exc),
                ],
            )

    # ==================================================
    # Redispatch
    # ==================================================

    @classmethod
    def _redispatch_after_offer(
        cls,
        offer,
        status,
        warning,
    ):
        """
        Redispatch a delivery after an offer reaches a
        terminal offer state.

        The previous rider remains excluded because the
        DeliveryOffer history is the persistent source
        of truth.

        max_rider_assignments controls how many actual
        rider-assignment attempts may be made.

        A rejected/expired offer does not itself create
        an assignment.
        """

        if offer is None:
            raise InvalidOfferState(
                "Delivery offer is required "
                "for redispatch."
            )

        delivery = offer.delivery

        # ----------------------------------------------
        # Validate delivery
        # ----------------------------------------------

        if cls._delivery_is_terminal(
            delivery,
        ):
            return DispatchResult.success_result(
                status=status,
                message=(
                    "Delivery is no longer "
                    "eligible for redispatch."
                ),
                delivery=delivery,
                offer=offer,
            )

        # ----------------------------------------------
        # Load configuration
        # ----------------------------------------------

        config = (
            DispatchConfigurationService
            .get_configuration()
        )

        if config is None:
            raise DispatchConfigurationError(
                "No active dispatch configuration "
                "is available."
            )

        # ----------------------------------------------
        # Automatic redispatch disabled
        # ----------------------------------------------

        if not config.auto_redispatch:

            return DispatchResult.success_result(
                status=status,
                message=(
                    f"Delivery offer "
                    f"{status.lower()}. "
                    "Automatic redispatch is disabled."
                ),
                delivery=delivery,
                offer=offer,
            )

        # ----------------------------------------------
        # Maximum rider assignment check
        # ----------------------------------------------

        if cls._maximum_rider_assignments_reached(
            delivery=delivery,
            config=config,
        ):
            result = DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=(
                    "Maximum rider assignment "
                    "attempts have been reached."
                ),
                delivery=delivery,
                offer=offer,
                errors=[
                    "Maximum rider assignment limit reached.",
                ],
            )

            result.add_warning(
                warning,
            )

            return result

        # ----------------------------------------------
        # Persistent exclusions
        # ----------------------------------------------

        excluded_rider_ids = (
            cls._get_excluded_rider_ids(
                delivery=delivery,
            )
        )

        # ----------------------------------------------
        # Next dispatch attempt
        # ----------------------------------------------

        attempt = cls._get_current_attempt(
            delivery,
        )

        # ----------------------------------------------
        # Redispatch
        # ----------------------------------------------

        redispatch_result = cls.dispatch(
            delivery=delivery,
            excluded_rider_ids=excluded_rider_ids,
            attempt=attempt,
        )

        # ----------------------------------------------
        # Preserve previous offer information
        # ----------------------------------------------

        if redispatch_result.context is not None:

            redispatch_result.context.add_metadata(
                "previous_offer_id",
                offer.id,
            )

            redispatch_result.context.add_metadata(
                "previous_offer_status",
                offer.status,
            )

            redispatch_result.context.add_warning(
                warning,
            )

        else:

            redispatch_result.add_warning(
                warning,
            )

        return redispatch_result

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

        if offer is None:
            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message="Delivery offer is required.",
                errors=[
                    "Offer cannot be None.",
                ],
            )

        try:

            cancelled_offer = (
                DeliveryOfferService.cancel(
                    offer=offer,
                )
            )

            return DispatchResult.success_result(
                status=DispatchStatus.CANCELLED,
                message="Delivery offer cancelled.",
                delivery=cancelled_offer.delivery,
                offer=cancelled_offer,
            )

        except InvalidOfferState as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=str(exc),
                delivery=offer.delivery,
                offer=offer,
                errors=[
                    str(exc),
                ],
            )

        except Exception as exc:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=(
                    "Unable to cancel "
                    "delivery offer."
                ),
                delivery=offer.delivery,
                offer=offer,
                errors=[
                    str(exc),
                ],
            )

    # ==================================================
    # Event Publishing
    # ==================================================

    @staticmethod
    def _publish_after_commit(
        event,
    ):
        """
        Publish an event after the current database
        transaction successfully commits.
        """

        transaction.on_commit(
            lambda event=event: (
                EventPublisher.publish(
                    event,
                )
            )
        )

    # ==================================================
    # Offer Notifications
    # ==================================================

    @staticmethod
    def _notify_offer_rejected(
        offer,
    ):
        """
        Notify that an offer was rejected.

        Notification failure does not invalidate the
        persisted rejection.
        """

        try:

            DispatchNotifier.notify_offer_rejected(
                offer,
            )

        except Exception:
            pass

    @staticmethod
    def _notify_offer_expired(
        offer,
    ):
        """
        Notify that an offer expired.

        Notification failure does not invalidate the
        persisted expiration.
        """

        try:

            DispatchNotifier.notify_offer_expired(
                offer,
            )

        except Exception:
            pass

    # ==================================================
    # Persistent Rider Exclusions
    # ==================================================

    @staticmethod
    def _get_excluded_rider_ids(
        delivery,
    ):
        """
        Return rider IDs that have already received
        an offer for this delivery.

        DeliveryOffer is the persistent source of truth
        for rider dispatch history.

        Any rider with a DeliveryOffer record is treated
        as previously attempted.
        """

        if delivery is None:
            return set()

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
    # Current Dispatch Attempt
    # ==================================================

    @staticmethod
    def _get_current_attempt(
        delivery,
    ):
        """
        Determine the next dispatch attempt number.

        This number represents dispatch cycles/offers,
        not completed assignments.

        Examples:

            No previous offers:
                attempt = 1

            One previous offer:
                attempt = 2

            Two previous offers:
                attempt = 3

        The assignment limit is enforced separately by
        _maximum_rider_assignments_reached().
        """

        if delivery is None:
            return 1

        previous_offers = (
            DeliveryOffer.objects
            .filter(
                delivery=delivery,
            )
            .count()
        )

        return previous_offers + 1

    # ==================================================
    # Maximum Rider Assignments
    # ==================================================

    @staticmethod
    def _get_maximum_rider_assignments(
        config,
    ):
        """
        Return the configured maximum number of rider
        assignments.

        Configuration field:

            max_rider_assignments

        Semantics:

            <= 0
                unlimited

            > 0
                maximum number of assignment records
                allowed for the delivery.
        """

        if config is None:
            return 0

        value = getattr(
            config,
            "max_rider_assignments",
            0,
        )

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
            return 0

    # ==================================================
    # Completed Assignments
    # ==================================================

    @staticmethod
    def _get_completed_assignment_count(
        delivery,
    ):
        """
        Return the number of rider assignments already
        created for the delivery.

        DeliveryAssignment is the source of truth.

        This is intentionally NOT derived from
        DeliveryOffer count.
        """

        if delivery is None:
            return 0

        return (
            DeliveryAssignment.objects
            .filter(
                delivery=delivery,
            )
            .count()
        )

    # ==================================================
    # Maximum Assignment Validation
    # ==================================================

    @classmethod
    def _maximum_rider_assignments_reached(
        cls,
        delivery,
        config,
    ):
        """
        Determine whether the maximum number of rider
        assignments has been reached.

        Important
        ---------
        This checks actual DeliveryAssignment records.

        DeliveryOffer records do NOT count as assignments.

        Therefore:

            5 rejected offers
            +
            0 assignments

        does NOT mean that 5 assignments have occurred.

        Example:

            max_rider_assignments = 3

            assignments = 0
                -> dispatch allowed

            assignments = 1
                -> dispatch allowed

            assignments = 2
                -> dispatch allowed

            assignments = 3
                -> dispatch blocked
        """

        maximum = (
            cls._get_maximum_rider_assignments(
                config,
            )
        )

        # ----------------------------------------------
        # Unlimited
        # ----------------------------------------------

        if maximum <= 0:
            return False

        # ----------------------------------------------
        # Actual assignments
        # ----------------------------------------------

        assignment_count = (
            cls._get_completed_assignment_count(
                delivery,
            )
        )

        return assignment_count >= maximum

    # ==================================================
    # Delivery State
    # ==================================================

    @staticmethod
    def _delivery_is_terminal(
        delivery,
    ):
        """
        Determine whether dispatch should no longer run.

        Terminal states:

            DELIVERED
            CANCELLED

        FAILED remains retryable.
        """

        if delivery is None:
            return True

        terminal_statuses = {
            Delivery.DeliveryStatus.DELIVERED,
            Delivery.DeliveryStatus.CANCELLED,
        }

        return (
            delivery.status
            in terminal_statuses
        )
