from django.db import transaction
from ..models import DeliveryAssignment, Delivery


class AssignmentService:
    @staticmethod
    @transaction.atomic
    def assign(
        delivery,
        rider,
        assigned_by=None,
    ):

        assignment = DeliveryAssignment.objects.create(
            delivery=delivery,
            rider=rider,
            assigned_by=assigned_by,
            status=DeliveryAssignment.AssignmentStatus.ASSIGNED,
        )

        delivery.status = (
            Delivery.DeliveryStatus.RIDER_ASSIGNED
        )

        delivery.save(
            update_fields=["status"]
        )

        return assignment