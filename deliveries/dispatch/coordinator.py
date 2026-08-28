from django.db import transaction

from deliveries.constants import DeliveryOfferAction
from deliveries.models.delivery import Delivery
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

    The coordinator orchestrates the dispatch lifecycle.

    It does NOT contain:

        • Rider eligibility logic
        • Distance calculation
        • Rider scoring
        • Strategy calculations
        • Offer state-transition logic
        • Assignment business logic

    Those responsibilities belong to their respective
    services.

    Persistent rider-attempt history is derived from
    DeliveryOffer records.

    DispatchContext stores the in-memory state of the
    current dispatch attempt.
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

        The delivery-created event is published after
        the current transaction commits.

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

            # Event publication must not prevent the
            # delivery from entering dispatch.

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

        Persistent DeliveryOffer history is used to
        determine riders that have already received an
        offer for the delivery.

        Explicit exclusions are merged with persistent
        exclusions.

        Parameters
        ----------
        delivery:
            Delivery being dispatched.

        excluded_rider_ids:
            Optional rider IDs that should be excluded
            from this dispatch attempt.

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
            # Determine attempt
            # ------------------------------------------

            if attempt is None:

                attempt = cls._get_current_attempt(
                    delivery,
                )

            # ------------------------------------------
            # Normalize attempt
            # ------------------------------------------

            try:

                attempt = int(
                    attempt,
                )

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
            # Attempt limit
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
            # Create dispatch context
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

            if (
                result.status
                == DispatchStatus.FAILED
            ):

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

        Notification failure must never propagate back
        into dispatch processing.
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

        # ----------------------------------------------
        # Validate offer
        # ----------------------------------------------

        if offer is None:

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message="Delivery offer is required.",
                errors=[
                    "Offer cannot be None.",
                ],
            )

        # ----------------------------------------------
        # Accept
        # ----------------------------------------------

        if action == DeliveryOfferAction.ACCEPT:

            return cls._accept_offer(
                offer=offer,
            )

        # ----------------------------------------------
        # Reject
        # ----------------------------------------------

        if action == DeliveryOfferAction.REJECT:

            return cls._reject_offer(
                offer=offer,
                reason=reason,
            )

        # ----------------------------------------------
        # Invalid action
        # ----------------------------------------------

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

        The delivery is locked first.

        DeliveryOfferService.accept() is responsible
        for locking and validating the offer itself.

        Assignment creation and offer acceptance occur
        within the same transaction.
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
                # Return success
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

        If automatic redispatch is enabled, the delivery
        is sent through another dispatch attempt.

        The rejected rider remains permanently excluded
        because DeliveryOffer history is the persistent
        source of truth.
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
            # Publish rejection event
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
            # Publish expiration event
            # ------------------------------------------

            cls._publish_after_commit(
                DeliveryOfferExpiredEvent(
                    offer=expired_offer,
                )
            )

            # ------------------------------------------
            # Notify rider
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

        The previous offer is never returned as the
        current offer.

        If redispatch succeeds:

            result.offer

        contains the NEW offer.

        Metadata records the previous offer.
        """

        delivery = offer.delivery

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
        # Persistent exclusions
        # ----------------------------------------------

        excluded_rider_ids = (
            cls._get_excluded_rider_ids(
                delivery=delivery,
            )
        )

        # ----------------------------------------------
        # Next attempt
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

            # ------------------------------------------
            # Cancel offer
            # ------------------------------------------

            cancelled_offer = (
                DeliveryOfferService.cancel(
                    offer=offer,
                )
            )

            # ------------------------------------------
            # Return result
            # ------------------------------------------

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

        When called outside a transaction, Django's
        current transaction is effectively committed
        immediately, so the event is published normally.
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

        Notification failure must not invalidate the
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

        Notification failure must not invalidate the
        persisted expiration.
        """

        try:

            DispatchNotifier.notify_offer_expired(
                offer,
            )

        except Exception:

            pass

    # ==================================================
    # Persistent Exclusions
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
    # Current Attempt
    # ==================================================

    @staticmethod
    def _get_current_attempt(
        delivery,
    ):
        """
        Determine the next dispatch attempt number.

        Every historical DeliveryOffer represents one
        rider offer attempt.

        Examples:

            No previous offers:
                attempt = 1

            One previous offer:
                attempt = 2

            Two previous offers:
                attempt = 3
        """

        if delivery is None:

            return 1

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

        A maximum value <= 0 means unlimited attempts.
        """

        if config is None:

            return True

        maximum_attempts = getattr(
            config,
            "max_assignment_attempts",
            0,
        )

        try:

            maximum_attempts = int(
                maximum_attempts,
            )

        except (
            TypeError,
            ValueError,
        ):

            return True

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