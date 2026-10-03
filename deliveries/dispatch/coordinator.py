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

    See module docstring in the original for the full responsibility
    list.

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

        if transaction.get_autocommit():
            cls._publish_delivery_created(delivery)

            try:
                return cls.dispatch(delivery)
            except Exception as exc:
                return cls._dispatch_failure(
                    delivery=delivery,
                    exception=exc,
                )

        # NOTE: order matters. Register publish first, dispatch second,
        # so that on-commit execution publishes the creation event
        # before beginning dispatch.
        transaction.on_commit(
            lambda delivery_id=delivery_id: (
                cls._publish_delivery_created_by_id(delivery_id)
            )
        )

        transaction.on_commit(
            lambda delivery_id=delivery_id: cls._dispatch_after_commit(
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
        """

        if delivery is None:
            raise ValueError("delivery is required.")

        excluded_rider_ids = set(excluded_rider_ids or [])

        try:
            delivery = cls._lock_delivery(delivery.pk)

            if cls._delivery_is_terminal(delivery):
                return DispatchResult.failed(
                    delivery=delivery,
                    status=DispatchStatus.FAILED,
                    message=(
                        f"Delivery {delivery.tracking_number} "
                        "cannot be dispatched because it is terminal."
                    ),
                )

            config = DispatchConfigurationService.get_active_config()

            if config is None:
                raise DispatchConfigurationError(
                    "No active dispatch configuration is available."
                )

            if attempt is None:
                attempt = cls._get_current_attempt(delivery)

            cls._validate_attempt(attempt)

            persistent_excluded_rider_ids = (
                cls._get_excluded_rider_ids(delivery)
            )

            excluded_rider_ids.update(
                persistent_excluded_rider_ids
            )

            context = DispatchContext(
                delivery=delivery,
                config=config,
                customer=delivery.customer,
                vendor=delivery.vendor,
                store=getattr(delivery, "pickup_store", None),
                attempt=attempt,
                excluded_rider_ids=excluded_rider_ids,
            )

            context.metadata.update(
                {
                    "dispatch_attempt": attempt,
                    "persistent_excluded_rider_count": len(
                        persistent_excluded_rider_ids
                    ),
                }
            )

            result = DispatchPipeline(context).run()

            if getattr(result, "status", None) == DispatchStatus.FAILED:
                cls._notify_dispatch_failed(
                    delivery=delivery,
                    result=result,
                )

            return result

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
        reason="",
    ):
        """
        Handle a rider's response to a delivery offer.

        Supported actions:
            ACCEPT
            REJECT

        `reason` is only meaningful for REJECT.
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
                reason=reason,
            )

        raise ValueError(
            f"Unsupported delivery offer action: {action}"
        )

    # ------------------------------------------------------------------

    @classmethod
    def offer_expired(cls, offer):
        """
        Handle offer expiration.
        """

        if offer is None:
            raise ValueError("offer is required.")

        try:
            with transaction.atomic():
                cls._lock_delivery(offer.delivery_id)

                expired_offer = DeliveryOfferService.expire(
                    offer=offer,
                )

            cls._notify_offer_expired(expired_offer)

            return cls._redispatch_after_offer(
                expired_offer,
                reason="offer_expired",
            )

        except InvalidOfferState:
            raise

        except Exception:
            raise

    # ------------------------------------------------------------------

    @classmethod
    def cancel_offer(cls, offer):
        """
        Cancel an offer without automatically redispatching.
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
        """

        try:
            with transaction.atomic():

                delivery = cls._lock_delivery(offer.delivery_id)

                locked_offer = (
                    DeliveryOffer.objects
                    .select_for_update()
                    .select_related("rider")
                    .get(pk=offer.pk)
                )

                if rider is not None:
                    if locked_offer.rider_id != rider.pk:
                        raise InvalidOfferState(
                            "This offer does not belong to the rider."
                        )

                if cls._delivery_is_terminal(delivery):
                    raise InvalidOfferState(
                        "This delivery can no longer accept an offer."
                    )

                accepted_offer = DeliveryOfferService.accept(
                    offer=locked_offer,
                )

                assignment = AssignmentService.assign(
                    delivery=delivery,
                    rider=accepted_offer.rider,
                )

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
        reason="",
    ):
        """
        Reject an offer and optionally redispatch.

        `reason` is forwarded to DeliveryOfferService.reject() and
        recorded on the offer's rejection_reason field.
        """

        if offer is None:
            raise ValueError("offer is required.")

        try:
            with transaction.atomic():

                cls._lock_delivery(offer.delivery_id)

                if rider is not None and offer.rider_id != rider.pk:
                    raise InvalidOfferState(
                        "This offer does not belong to the rider."
                    )

                rejected_offer = DeliveryOfferService.reject(
                    offer=offer,
                    reason=reason,
                )

            cls._notify_offer_rejected(rejected_offer)

            return cls._redispatch_after_offer(
                rejected_offer,
                reason="offer_rejected",
            )

        except InvalidOfferState as exc:
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

        Does not lock the delivery here; dispatch() owns the lock.
        """

        if offer is None:
            raise ValueError("offer is required.")

        try:
            try:
                delivery = (
                    Delivery.objects
                    .select_related(
                        "customer",
                        "vendor",
                        "pickup_store",
                    )
                    .get(pk=offer.delivery_id)
                )
            except Delivery.DoesNotExist:
                return DispatchResult.failed(
                    delivery=None,
                    status=DispatchStatus.FAILED,
                    message="Delivery does not exist.",
                )

            if cls._delivery_is_terminal(delivery):
                return DispatchResult.failed(
                    delivery=delivery,
                    status=DispatchStatus.FAILED,
                    message=(
                        "Delivery is terminal and cannot be "
                        "redispatched."
                    ),
                )

            config = DispatchConfigurationService.get_active_config()

            if config is None:
                raise DispatchConfigurationError(
                    "No active dispatch configuration is available."
                )

            if not getattr(config, "auto_redispatch", False):
                return DispatchResult.failed(
                    delivery=delivery,
                    status=DispatchStatus.FAILED,
                    message="Automatic redispatch is disabled.",
                )

            excluded_rider_ids = cls._get_excluded_rider_ids(delivery)

            attempt = cls._get_current_attempt(delivery)

            result = cls.dispatch(
                delivery=delivery,
                excluded_rider_ids=excluded_rider_ids,
                attempt=attempt,
            )

            if hasattr(result, "metadata") and result.metadata is not None:
                result.metadata.update(
                    {
                        "redispatch": True,
                        "redispatch_reason": reason,
                        "previous_offer_id": str(offer.pk),
                        "previous_offer_rider_id": offer.rider_id,
                        "excluded_rider_count": len(excluded_rider_ids),
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
        return set(
            DeliveryOffer.objects
            .filter(delivery_id=delivery.pk)
            .values_list("rider_id", flat=True)
        )

    # ------------------------------------------------------------------

    @classmethod
    def _get_current_attempt(cls, delivery):
        """
        Attempt = distinct riders already offered this delivery + 1.
        """
        distinct_rider_count = (
            DeliveryOffer.objects
            .filter(delivery_id=delivery.pk)
            .values("rider_id")
            .distinct()
            .count()
        )
        return distinct_rider_count + 1

    # ------------------------------------------------------------------

    @staticmethod
    def _validate_attempt(attempt):
        if not isinstance(attempt, int):
            raise DispatchConfigurationError(
                "Dispatch attempt must be an integer."
            )
        if attempt <= 0:
            raise DispatchConfigurationError(
                "Dispatch attempt must be greater than zero."
            )

    # ------------------------------------------------------------------
    # Delivery terminal-state handling
    # ------------------------------------------------------------------

    @staticmethod
    def _delivery_is_terminal(delivery):
        property_value = getattr(
            delivery,
            "is_dispatch_terminal",
            None,
        )

        if isinstance(property_value, bool):
            return property_value

        return delivery.status in {
            Delivery.DeliveryStatus.DELIVERED,
            Delivery.DeliveryStatus.CANCELLED,
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
        try:
            DispatchNotifier.offer_rejected(offer=offer)
        except Exception:
            pass

    # ------------------------------------------------------------------

    @staticmethod
    def _notify_offer_expired(offer):
        try:
            DispatchNotifier.offer_expired(offer=offer)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Delivery-created event
    # ------------------------------------------------------------------

    @staticmethod
    def _publish_delivery_created(delivery):
        try:
            EventPublisher.publish(
                DeliveryCreatedEvent(delivery=delivery)
            )
        except Exception:
            pass

    # ------------------------------------------------------------------

    @classmethod
    def _publish_delivery_created_by_id(cls, delivery_id):
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
            cls._publish_delivery_created(delivery)
        except Delivery.DoesNotExist:
            pass
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Dispatch-after-commit
    # ------------------------------------------------------------------

    @classmethod
    def _dispatch_after_commit(cls, delivery_id):
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
            return cls.dispatch(delivery=delivery)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Offer accepted event
    # ------------------------------------------------------------------

    @classmethod
    def _publish_offer_accepted_by_id(cls, assignment_id):
        try:
            assignment = (
                DeliveryAssignment.objects
                .select_related("delivery", "rider")
                .get(pk=assignment_id)
            )
        except DeliveryAssignment.DoesNotExist:
            return

        cls._publish_offer_accepted(assignment)

    # ------------------------------------------------------------------

    @staticmethod
    def _publish_offer_accepted(assignment):
        try:
            EventPublisher.publish(
                DeliveryOfferAcceptedEvent(assignment=assignment)
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Generic after-commit publisher
    # ------------------------------------------------------------------

    @staticmethod
    def _publish_after_commit(event):
        def publish():
            try:
                EventPublisher.publish(event)
            except Exception:
                pass

        transaction.on_commit(publish)