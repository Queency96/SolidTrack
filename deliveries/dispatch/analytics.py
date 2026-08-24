from deliveries.models.models import (
    Delivery,
    DeliveryAssignment,
    DeliveryOffer,
)


class DispatchAnalyticsService:
    """
    Provides aggregated analytics for the dispatch subsystem.
    """

    # ==================================================
    # Public API
    # ==================================================

    @classmethod
    def dashboard(
        cls,
        *,
        start_date=None,
        end_date=None,
    ):
        deliveries = cls._delivery_queryset(
            start_date=start_date,
            end_date=end_date,
        )

        offers = cls._offer_queryset(
            start_date=start_date,
            end_date=end_date,
        )

        assignments = cls._assignment_queryset(
            start_date=start_date,
            end_date=end_date,
        )

        return {
            "period": {
                "start": start_date,
                "end": end_date,
            },
            "overview": cls._overview(
                deliveries=deliveries,
                assignments=assignments,
            ),
            "offers": cls._offer_statistics(
                offers=offers,
            ),
            "assignments": cls._assignment_statistics(
                assignments=assignments,
            ),
            "response": cls._response_statistics(
                offers=offers,
            ),
            "active": cls._active_statistics(),
        }

    # ==================================================
    # Overview
    # ==================================================

    @classmethod
    def _overview(
        cls,
        *,
        deliveries,
        assignments,
    ):
        total_deliveries = deliveries.count()

        assigned_deliveries = (
            assignments.values(
                "delivery_id"
            )
            .distinct()
            .count()
        )

        completed_deliveries = (
            assignments.filter(
                status=(
                    DeliveryAssignment
                    .AssignmentStatus
                    .COMPLETED
                )
            )
            .values("delivery_id")
            .distinct()
            .count()
        )

        cancelled_deliveries = (
            assignments.filter(
                status=(
                    DeliveryAssignment
                    .AssignmentStatus
                    .CANCELLED
                )
            )
            .values("delivery_id")
            .distinct()
            .count()
        )

        failed_deliveries = max(
            total_deliveries
            - assigned_deliveries,
            0,
        )

        return {
            "total_deliveries": total_deliveries,
            "assigned_deliveries": assigned_deliveries,
            "completed_deliveries": completed_deliveries,
            "cancelled_deliveries": cancelled_deliveries,
            "failed_deliveries": failed_deliveries,
            "assignment_rate": cls._percentage(
                assigned_deliveries,
                total_deliveries,
            ),
            "completion_rate": cls._percentage(
                completed_deliveries,
                assigned_deliveries,
            ),
        }

    # ==================================================
    # Offer Statistics
    # ==================================================

    @classmethod
    def _offer_statistics(
        cls,
        *,
        offers,
    ):
        total = offers.count()

        pending = offers.filter(
            status=DeliveryOffer.Status.PENDING
        ).count()

        accepted = offers.filter(
            status=DeliveryOffer.Status.ACCEPTED
        ).count()

        rejected = offers.filter(
            status=DeliveryOffer.Status.REJECTED
        ).count()

        expired = offers.filter(
            status=DeliveryOffer.Status.EXPIRED
        ).count()

        cancelled = offers.filter(
            status=DeliveryOffer.Status.CANCELLED
        ).count()

        return {
            "total": total,
            "pending": pending,
            "accepted": accepted,
            "rejected": rejected,
            "expired": expired,
            "cancelled": cancelled,
            "acceptance_rate": cls._percentage(
                accepted,
                total,
            ),
            "rejection_rate": cls._percentage(
                rejected,
                total,
            ),
            "expiry_rate": cls._percentage(
                expired,
                total,
            ),
        }

    # ==================================================
    # Assignment Statistics
    # ==================================================

    @classmethod
    def _assignment_statistics(
        cls,
        *,
        assignments,
    ):
        total = assignments.count()

        assigned = assignments.filter(
            status=DeliveryAssignment.AssignmentStatus.ASSIGNED
        ).count()

        accepted = assignments.filter(
            status=DeliveryAssignment.AssignmentStatus.ACCEPTED
        ).count()

        completed = assignments.filter(
            status=DeliveryAssignment.AssignmentStatus.COMPLETED
        ).count()

        cancelled = assignments.filter(
            status=DeliveryAssignment.AssignmentStatus.CANCELLED
        ).count()

        reassigned = assignments.filter(
            status=DeliveryAssignment.AssignmentStatus.REASSIGNED
        ).count()

        return {
            "total": total,
            "assigned": assigned,
            "accepted": accepted,
            "completed": completed,
            "cancelled": cancelled,
            "reassigned": reassigned,
            "completion_rate": cls._percentage(
                completed,
                total,
            ),
            "cancellation_rate": cls._percentage(
                cancelled,
                total,
            ),
        }

    # ==================================================
    # Response Statistics
    # ==================================================

    @classmethod
    def _response_statistics(
        cls,
        *,
        offers,
    ):
        responded = offers.filter(
            responded_at__isnull=False,
        )

        response_times = []

        for offer in responded.only(
            "created_at",
            "responded_at",
        ):
            if (
                offer.created_at
                and offer.responded_at
            ):
                response_times.append(
                    (
                        offer.responded_at
                        - offer.created_at
                    ).total_seconds()
                )

        average_seconds = (
            sum(response_times)
            / len(response_times)
            if response_times
            else 0
        )

        return {
            "responded_offers": responded.count(),
            "average_response_seconds": round(
                average_seconds,
                2,
            ),
            "average_response_minutes": round(
                average_seconds / 60,
                2,
            ),
        }

    # ==================================================
    # Active Statistics
    # ==================================================

    @classmethod
    def _active_statistics(cls):
        pending_offers = DeliveryOffer.objects.filter(
            status=DeliveryOffer.Status.PENDING,
        ).count()

        active_assignments = (
            DeliveryAssignment.objects.exclude(
                status__in=[
                    DeliveryAssignment.AssignmentStatus.COMPLETED,
                    DeliveryAssignment.AssignmentStatus.CANCELLED,
                    DeliveryAssignment.AssignmentStatus.REASSIGNED,
                ]
            ).count()
        )

        active_deliveries = Delivery.objects.filter(
            status__in=[
                Delivery.DeliveryStatus.RIDER_ASSIGNED,
                Delivery.DeliveryStatus.IN_TRANSIT,
            ]
        ).count()

        return {
            "pending_offers": pending_offers,
            "active_assignments": active_assignments,
            "active_deliveries": active_deliveries,
        }

    # ==================================================
    # Querysets
    # ==================================================

    @staticmethod
    def _delivery_queryset(
        *,
        start_date=None,
        end_date=None,
    ):
        queryset = Delivery.objects.all()

        if start_date:
            queryset = queryset.filter(
                created_at__gte=start_date
            )

        if end_date:
            queryset = queryset.filter(
                created_at__lte=end_date
            )

        return queryset

    @staticmethod
    def _offer_queryset(
        *,
        start_date=None,
        end_date=None,
    ):
        queryset = DeliveryOffer.objects.all()

        if start_date:
            queryset = queryset.filter(
                created_at__gte=start_date
            )

        if end_date:
            queryset = queryset.filter(
                created_at__lte=end_date
            )

        return queryset

    @staticmethod
    def _assignment_queryset(
        *,
        start_date=None,
        end_date=None,
    ):
        queryset = DeliveryAssignment.objects.all()

        if start_date:
            queryset = queryset.filter(
                created_at__gte=start_date
            )

        if end_date:
            queryset = queryset.filter(
                created_at__lte=end_date
            )

        return queryset

    # ==================================================
    # Helpers
    # ==================================================

    @staticmethod
    def _percentage(
        numerator,
        denominator,
    ):
        if not denominator:
            return 0

        return round(
            (numerator / denominator) * 100,
            2,
        )