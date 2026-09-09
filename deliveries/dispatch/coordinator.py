from django.core.exceptions import ValidationError
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
    High-level orchestration service for the delivery dispatch lifecycle.

    Responsibilities
    ----------------
    - Coordinate delivery creation -> dispatch.
    - Coordinate offer responses.
    - Coordinate offer expiration/rejection -> redispatch.
    - Coordinate offer acceptance -> assignment.
    - Coordinate admin offer cancellation.
    - Publish domain events after transaction commit.
    - Trigger notifications on dispatch outcomes.

    This class intentionally does NOT own:
    - rider matching
    - rider ranking
    - rider eligibility
    - offer lifecycle
    - assignment lifecycle
    - rider availability logic

    Those responsibilities belong to the appropriate services.

    Assignment invariant
    --------------------
    A delivery has exactly ONE DeliveryAssignment row during its
    entire lifetime.

    A cancelled assignment may be reused only after an explicit
    administrative/staff restart puts the delivery back into
    WAITING_FOR_RIDER.

    A completed assignment can never be reused.

    Offer != Assignment
    --------------------
    Creating or accepting a DeliveryOffer does not itself create an
    assignment. AssignmentService is the final authority responsible
    for creating/reusing the single assignment row.

    Lock ordering
    -------------
    Global lock order:

        Delivery
            ->
        DeliveryOffer / DeliveryAssignment
            ->
        RiderProfile

    Never acquire these locks in reverse order.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def delivery_created(cls, delivery):
        """
        Entry point after a Delivery has been created.

        The DeliveryCreatedEvent MUST be published after the surrounding
        transaction commits.

        Dispatch is also deferred until commit when this method is called
        from inside an atomic transaction.
        """

        if delivery is None:
            raise ValueError("delivery is required.")

        delivery_id = delivery.pk

        # --------------------------------------------------------------
        # Autocommit mode
        # --------------------------------------------------------------
        #
        # There is no surrounding transaction to wait for.
        # Publish the event and dispatch immediately.
        #
        if transaction.get_autocommit():
            cls._publish_delivery_created(delivery)

            try:
                return cls.dispatch(delivery)
            except Exception as exc:
                return cls._dispatch_failure(
                    delivery=delivery,
                    exception=exc,
                )

        # --------------------------------------------------------------
        # Transaction mode
        # --------------------------------------------------------------
        #
        # The delivery may still be rolled back. Therefore neither the
        # event nor dispatch should happen before commit.
        #
        transaction.on_commit(
            lambda delivery_id=delivery_id: cls._dispatch_after_commit(
                delivery_id
            )
        )

        transaction.on_commit(
            lambda delivery_id=delivery_id: cls._publish_delivery_created_by_id(
                delivery_id
            )
        )

        return DispatchResult.created(
            delivery=delivery,
        )

    # ------------------------------------------------------------------

    @classmethod
    def dispatch(
        cls,
        delivery,
        excluded_rider_ids=None,
        attempt=None,
    ):
        """
        Start or retry dispatch for a delivery.

        Matching, ranking, eligibility and offer creation are delegated
        to DispatchPipeline.
        """

        if delivery is None:
            raise ValueError("delivery is required.")

        excluded_rider_ids = set(excluded_rider_ids or [])

        try:
            # ----------------------------------------------------------
            # Delivery MUST be the first database lock.
            # ----------------------------------------------------------
            delivery = cls._lock_delivery(delivery.pk)

            # ----------------------------------------------------------
            # DELIVERED and CANCELLED are dispatch-terminal.
            #
            # FAILED intentionally remains retryable.
            # ----------------------------------------------------------
            if cls._delivery_is_terminal(delivery):
                return DispatchResult.failed(
                    delivery=delivery,
                    status=DispatchStatus.FAILED,
                    message=(
                        f"Delivery {delivery.tracking_number} "
                        "cannot be dispatched because it is terminal."
                    ),
                )

            # ----------------------------------------------------------
            # Configuration
            # ----------------------------------------------------------
            config = DispatchConfigurationService.get_active_config()

            if config is None:
                raise DispatchConfigurationError(
                    "No active dispatch configuration is available."
                )

            # ----------------------------------------------------------
            # Determine attempt.
            # ----------------------------------------------------------
            if attempt is None:
                attempt = cls._get_current_attempt(delivery)

            cls._validate_attempt(attempt)

            # ----------------------------------------------------------
            # Persistent exclusions.
            #
            # A rider who already received an offer for this delivery
            # should not receive the same delivery again during automatic
            # redispatch.
            # ----------------------------------------------------------
            persistent_excluded_rider_ids = (
                cls._get_excluded_rider_ids(delivery)
            )

            excluded_rider_ids.update(
                persistent_excluded_rider_ids
            )

            # ----------------------------------------------------------
            # Build dispatch context.
            #
            # Delivery uses pickup_store, not store.
            # The context currently accepts "store" as its field name,
            # therefore we provide pickup_store through that field.
            # ----------------------------------------------------------
            context = DispatchContext(
                delivery=delivery,
                config=config,
                customer=delivery.customer,
                vendor=delivery.vendor,
                store=getattr(delivery, "pickup_store", None),
                attempt=attempt,
                excluded_rider_ids=excluded_rider_ids,
            )

            # ----------------------------------------------------------
            # Diagnostic metadata.
            # ----------------------------------------------------------
            context.metadata.update(
                {
                    "dispatch_attempt": attempt,
                    "persistent_excluded_rider_count": len(
                        persistent_excluded_rider_ids
                    ),
                    "maximum_rider_assignments": (
                        cls._get_maximum_rider_assignments(config)
                    ),
                    "actual_assignment_count": (
                        cls._get_assignment_count(delivery)
                    ),
                }
            )

            # ----------------------------------------------------------
            # Search -> rank -> eligibility -> offer -> notification.
            # ----------------------------------------------------------
            result = DispatchPipeline(context).run()

            # ----------------------------------------------------------
            # Pipeline failure notification.
            # ----------------------------------------------------------
            if getattr(result, "status", None) == DispatchStatus.FAILED:
                cls._notify_dispatch_failed(
                    delivery=delivery,
                    result=result,
                )

            return result

        except DispatchConfigurationError as exc:
            return cls._dispatch_failure(
                delivery=delivery,
                exception=exc,
            )

        except NoAvailableRider as exc:
            return cls._dispatch_failure(
                delivery=delivery,
                exception=exc,
            )

        except InvalidOfferState as exc:
            return cls._dispatch_failure(
                delivery=delivery,
                exception=exc,
            )

        except ValidationError as exc:
            return cls._dispatch_failure(
                delivery=delivery,
                exception=exc,
            )

        except Exception as exc:
            return cls._dispatch_failure(
                delivery=delivery,
                exception=exc,
            )

    # ------------------------------------------------------------------

    @classmethod
    def respond_to_offer(
        cls,
        *,
        offer,
        action,
        rider=None,
    ):
        """
        Handle a rider's response to a delivery offer.

        Supported actions:
            ACCEPT
            REJECT
        """

        if offer is None:
            raise ValueError("offer is required.")

        if not action:
            raise ValueError("action is required.")

        action = str(action).upper()

        if action == DeliveryOfferAction.ACCEPT:
            return cls._accept_offer(
                offer=offer,
                rider=rider,
            )

        if action == DeliveryOfferAction.REJECT:
            return cls._reject_offer(
                offer=offer,
                rider=rider,
            )

        raise ValueError(
            f"Unsupported delivery offer action: {action}"
        )

    # ------------------------------------------------------------------

    @classmethod
    def offer_expired(cls, offer):
        """
        Handle offer expiration.

        OfferService owns the offer lifecycle.

        Coordinator owns what happens next:
            expire -> notify -> redispatch
        """

        if offer is None:
            raise ValueError("offer is required.")

        try:
            expired_offer = DeliveryOfferService.expire(
                offer=offer,
            )

        except InvalidOfferState:
            raise

        except Exception:
            raise

        cls._notify_offer_expired(expired_offer)

        return cls._redispatch_after_offer(
            expired_offer,
            reason="offer_expired",
        )

    # ------------------------------------------------------------------

    @classmethod
    def cancel_offer(cls, offer):
        """
        Cancel an offer without automatically redispatching.

        This is intentionally different from rider rejection or
        automatic expiration.
        """

        if offer is None:
            raise ValueError("offer is required.")

        return DeliveryOfferService.cancel(
            offer=offer,
        )

    # ------------------------------------------------------------------
    # Offer acceptance
    # ------------------------------------------------------------------

    @classmethod
    def _accept_offer(
        cls,
        *,
        offer,
        rider=None,
    ):
        """
        Accept an offer and create/reuse the delivery assignment.

        Lock order:

            Delivery
                ->
            DeliveryOffer
                ->
            RiderProfile

        AssignmentService remains the sole authority for assignment
        creation/reuse.
        """

        try:
            with transaction.atomic():

                # ------------------------------------------------------
                # First lock Delivery.
                # ------------------------------------------------------
                delivery = cls._lock_delivery(
                    offer.delivery_id
                )

                # ------------------------------------------------------
                # Then lock Offer.
                # ------------------------------------------------------
                locked_offer = (
                    DeliveryOffer.objects
                    .select_for_update()
                    .select_related("rider")
                    .get(pk=offer.pk)
                )

                # ------------------------------------------------------
                # Validate rider ownership.
                # ------------------------------------------------------
                if rider is not None:
                    if locked_offer.rider_id != rider.pk:
                        raise InvalidOfferState(
                            "This offer does not belong to the rider."
                        )

                # ------------------------------------------------------
                # Delivery must still be dispatchable.
                # ------------------------------------------------------
                if cls._delivery_is_terminal(delivery):
                    raise InvalidOfferState(
                        "This delivery can no longer accept an offer."
                    )

                # ------------------------------------------------------
                # Offer lifecycle is owned by OfferService.
                # ------------------------------------------------------
                accepted_offer = DeliveryOfferService.accept(
                    offer=locked_offer,
                )

                # ------------------------------------------------------
                # Assignment lifecycle is owned by AssignmentService.
                # ------------------------------------------------------
                assignment = AssignmentService.assign(
                    delivery=delivery,
                    rider=accepted_offer.rider,
                )

                # ------------------------------------------------------
                # Publish only after the transaction commits.
                # ------------------------------------------------------
                transaction.on_commit(
                    lambda assignment_id=assignment.pk: (
                        cls._publish_offer_accepted_by_id(
                            assignment_id
                        )
                    )
                )

                return DispatchResult.assigned(
                    delivery=delivery,
                    assignment=assignment,
                    offer=accepted_offer,
                )

        except DeliveryOffer.DoesNotExist:
            return DispatchResult.failed(
                delivery=offer.delivery,
                status=DispatchStatus.FAILED,
                message="Delivery offer does not exist.",
            )

        except InvalidOfferState as exc:
            return DispatchResult.failed(
                delivery=offer.delivery,
                status=DispatchStatus.FAILED,
                message=str(exc),
            )

        except AssignmentAlreadyExists as exc:
            return DispatchResult.failed(
                delivery=offer.delivery,
                status=DispatchStatus.FAILED,
                message=str(exc),
            )

        except DispatchConfigurationError as exc:
            return DispatchResult.failed(
                delivery=offer.delivery,
                status=DispatchStatus.FAILED,
                message=str(exc),
            )

        except Exception as exc:
            return DispatchResult.failed(
                delivery=offer.delivery,
                status=DispatchStatus.FAILED,
                message=str(exc),
            )

    # ------------------------------------------------------------------
    # Offer rejection
    # ------------------------------------------------------------------

    @classmethod
    def _reject_offer(
        cls,
        *,
        offer,
        rider=None,
    ):
        """
        Reject an offer and optionally redispatch.

        Lifecycle:

            OfferService.reject()
                    |
                    v
                notify
                    |
                    v
                redispatch
        """

        if rider is not None and offer.rider_id != rider.pk:
            raise InvalidOfferState(
                "This offer does not belong to the rider."
            )

        rejected_offer = DeliveryOfferService.reject(
            offer=offer,
        )

        cls._notify_offer_rejected(
            rejected_offer
        )

        return cls._redispatch_after_offer(
            rejected_offer,
            reason="offer_rejected",
        )

    # ------------------------------------------------------------------
    # Redispatch
    # ------------------------------------------------------------------

    @classmethod
    def _redispatch_after_offer(
        cls,
        offer,
        reason,
    ):
        """
        Redispatch after a rejected or expired offer.

        Previously offered riders are excluded.

        No assignment-count precheck is performed here.

        AssignmentService remains the final authority regarding the
        single assignment-row invariant.
        """

        if offer is None:
            raise ValueError("offer is required.")

        try:
            # ----------------------------------------------------------
            # Delivery first.
            # ----------------------------------------------------------
            delivery = cls._lock_delivery(
                offer.delivery_id
            )

            # ----------------------------------------------------------
            # Dispatch-terminal states.
            #
            # FAILED is deliberately NOT included because FAILED
            # deliveries remain retryable.
            # ----------------------------------------------------------
            if cls._delivery_is_terminal(delivery):
                return DispatchResult.failed(
                    delivery=delivery,
                    status=DispatchStatus.FAILED,
                    message=(
                        "Delivery is terminal and cannot be "
                        "redispatched."
                    ),
                )

            # ----------------------------------------------------------
            # Configuration.
            # ----------------------------------------------------------
            config = DispatchConfigurationService.get_active_config()

            if config is None:
                raise DispatchConfigurationError(
                    "No active dispatch configuration is available."
                )

            # ----------------------------------------------------------
            # Respect automatic redispatch configuration.
            # ----------------------------------------------------------
            if not getattr(config, "auto_redispatch", False):
                return DispatchResult.failed(
                    delivery=delivery,
                    status=DispatchStatus.FAILED,
                    message=(
                        "Automatic redispatch is disabled."
                    ),
                )

            # ----------------------------------------------------------
            # Exclude every rider who already received an offer.
            # ----------------------------------------------------------
            excluded_rider_ids = cls._get_excluded_rider_ids(
                delivery
            )

            # ----------------------------------------------------------
            # Attempt number.
            # ----------------------------------------------------------
            attempt = cls._get_current_attempt(
                delivery
            )

            result = cls.dispatch(
                delivery=delivery,
                excluded_rider_ids=excluded_rider_ids,
                attempt=attempt,
            )

            # ----------------------------------------------------------
            # Add redispatch metadata.
            # ----------------------------------------------------------
            if hasattr(result, "metadata") and result.metadata is not None:
                result.metadata.update(
                    {
                        "redispatch": True,
                        "redispatch_reason": reason,
                        "previous_offer_id": str(
                            offer.pk
                        ),
                        "previous_offer_rider_id": (
                            offer.rider_id
                        ),
                        "excluded_rider_count": len(
                            excluded_rider_ids
                        ),
                    }
                )

            return result

        except DispatchConfigurationError as exc:
            return cls._dispatch_failure(
                delivery=offer.delivery,
                exception=exc,
            )

        except NoAvailableRider as exc:
            return cls._dispatch_failure(
                delivery=offer.delivery,
                exception=exc,
            )

        except Exception as exc:
            return cls._dispatch_failure(
                delivery=offer.delivery,
                exception=exc,
            )

    # ------------------------------------------------------------------
    # Database locking
    # ------------------------------------------------------------------

    @staticmethod
    def _lock_delivery(delivery_id):
        """
        Lock a Delivery before any Offer, Assignment or RiderProfile.

        This enforces the project's global lock order.
        """

        return (
            Delivery.objects
            .select_for_update()
            .select_related(
                "customer",
                "vendor",
                "pickup_store",
            )
            .get(pk=delivery_id)
        )

    # ------------------------------------------------------------------
    # Persistent exclusions
    # ------------------------------------------------------------------

    @staticmethod
    def _get_excluded_rider_ids(delivery):
        """
        Return all riders who have previously received an offer for
        this delivery.

        This prevents the same rider from receiving the same delivery
        repeatedly during automatic redispatch.
        """

        return set(
            DeliveryOffer.objects
            .filter(
                delivery_id=delivery.pk,
            )
            .exclude(
                rider_id__isnull=True,
            )
            .values_list(
                "rider_id",
                flat=True,
            )
        )

    # ------------------------------------------------------------------

    @classmethod
    def _get_current_attempt(cls, delivery):
        """
        Calculate the next dispatch attempt from the number of offers
        already generated for the delivery.
        """

        previous_offer_count = (
            DeliveryOffer.objects
            .filter(
                delivery_id=delivery.pk,
            )
            .count()
        )

        return previous_offer_count + 1

    # ------------------------------------------------------------------

    @staticmethod
    def _validate_attempt(attempt):
        """
        Validate dispatch attempt number.
        """

        if not isinstance(attempt, int):
            raise DispatchConfigurationError(
                "Dispatch attempt must be an integer."
            )

        if attempt <= 0:
            raise DispatchConfigurationError(
                "Dispatch attempt must be greater than zero."
            )

    # ------------------------------------------------------------------
    # Assignment information
    # ------------------------------------------------------------------

    @staticmethod
    def _get_assignment_count(delivery):
        """
        Return the number of assignment rows belonging to the delivery.

        Under the new architecture this should normally be:

            0 -> no assignment yet
            1 -> assignment exists

        The coordinator treats this as informational only.
        """

        return (
            DeliveryAssignment.objects
            .filter(
                delivery_id=delivery.pk,
            )
            .count()
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _get_maximum_rider_assignments(config):
        """
        Return the configured maximum rider assignment value when
        available.

        This is diagnostic metadata only.

        The coordinator does NOT use it to independently reject
        dispatch. AssignmentService owns assignment enforcement.
        """

        return getattr(
            config,
            "maximum_rider_assignments",
            getattr(
                config,
                "max_rider_assignments",
                None,
            ),
        )

    # ------------------------------------------------------------------
    # Delivery terminal-state handling
    # ------------------------------------------------------------------

    @staticmethod
    def _delivery_is_terminal(delivery):
        """
        Return whether dispatch is permanently forbidden.

        IMPORTANT:

        FAILED is intentionally NOT dispatch-terminal.

        A failed delivery can be retried.

        Only:
            DELIVERED
            CANCELLED

        are terminal from the coordinator's dispatch perspective.
        """

        return delivery.status in {
            Delivery.Status.DELIVERED,
            Delivery.Status.CANCELLED,
        }

    # ------------------------------------------------------------------
    # Failure handling
    # ------------------------------------------------------------------

    @classmethod
    def _dispatch_failure(
        cls,
        *,
        delivery,
        exception,
    ):
        """
        Convert an exception into a standardized DispatchResult.

        Notification failure must never mask the actual dispatch
        failure.
        """

        message = str(exception)

        cls._notify_dispatch_failed(
            delivery=delivery,
            exception=exception,
        )

        return DispatchResult.failed(
            delivery=delivery,
            status=DispatchStatus.FAILED,
            message=message,
        )

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    @staticmethod
    def _notify_dispatch_failed(
        *,
        delivery,
        result=None,
        exception=None,
    ):
        """
        Best-effort dispatch failure notification.

        Notification failures must never break dispatch.
        """

        try:
            DispatchNotifier.dispatch_failed(
                delivery=delivery,
                result=result,
                exception=exception,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------

    @staticmethod
    def _notify_offer_rejected(offer):
        """
        Best-effort offer rejection notification.
        """

        try:
            DispatchNotifier.offer_rejected(
                offer=offer,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------

    @staticmethod
    def _notify_offer_expired(offer):
        """
        Best-effort offer expiration notification.
        """

        try:
            DispatchNotifier.offer_expired(
                offer=offer,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Delivery-created event
    # ------------------------------------------------------------------

    @staticmethod
    def _publish_delivery_created(delivery):
        """
        Publish DeliveryCreatedEvent.

        Best effort: event publishing must never break delivery
        creation/dispatch.
        """

        try:
            EventPublisher.publish(
                DeliveryCreatedEvent(
                    delivery=delivery,
                )
            )
        except Exception:
            pass

    # ------------------------------------------------------------------

    @classmethod
    def _publish_delivery_created_by_id(cls, delivery_id):
        """
        Re-fetch the delivery after commit before publishing the event.

        This avoids publishing an event from an object whose transaction
        may have changed before commit.
        """

        try:
            delivery = (
                Delivery.objects
                .select_related(
                    "customer",
                    "vendor",
                    "pickup_store",
                )
                .get(pk=delivery_id)
            )

            cls._publish_delivery_created(
                delivery
            )

        except Delivery.DoesNotExist:
            pass

        except Exception:
            pass

    # ------------------------------------------------------------------
    # Dispatch-after-commit
    # ------------------------------------------------------------------

    @classmethod
    def _dispatch_after_commit(cls, delivery_id):
        """
        Dispatch a newly-created delivery after its transaction
        successfully commits.

        This function intentionally re-queries the Delivery instead of
        using the original object.
        """

        try:
            delivery = (
                Delivery.objects
                .select_related(
                    "customer",
                    "vendor",
                    "pickup_store",
                )
                .get(pk=delivery_id)
            )

        except Delivery.DoesNotExist:
            return None

        try:
            return cls.dispatch(
                delivery=delivery,
            )

        except Exception:
            # Dispatch itself normally standardizes failures, but this
            # final guard prevents an on_commit callback from escaping
            # unexpectedly.
            return None

    # ------------------------------------------------------------------
    # Offer accepted event
    # ------------------------------------------------------------------

    @classmethod
    def _publish_offer_accepted_by_id(cls, assignment_id):
        """
        Re-fetch the assignment after commit and publish the accepted
        offer event.

        Event publication is best effort.
        """

        try:
            assignment = (
                DeliveryAssignment.objects
                .select_related(
                    "delivery",
                    "rider",
                )
                .get(pk=assignment_id)
            )

        except DeliveryAssignment.DoesNotExist:
            return

        cls._publish_offer_accepted(
            assignment
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _publish_offer_accepted(assignment):
        """
        Publish DeliveryOfferAcceptedEvent.

        Event publication must never break the assignment transaction.
        """

        try:
            EventPublisher.publish(
                DeliveryOfferAcceptedEvent(
                    assignment=assignment,
                )
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Generic after-commit publisher
    # ------------------------------------------------------------------

    @staticmethod
    def _publish_after_commit(event):
        """
        Register a generic event for after-commit publication.

        Useful for future coordinator events.

        The callback is intentionally best effort.
        """

        def publish():
            try:
                EventPublisher.publish(event)
            except Exception:
                pass

        transaction.on_commit(
            publish
        )