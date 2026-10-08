import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from deliveries.models import Delivery
from order.services.order_fulfillment_service import (
    OrderFulfillmentService,
)


logger = logging.getLogger(__name__)


@require_POST
def verify_delivery_otp(request, delivery_id):
    """
    Rider confirms handover by entering the OTP the
    customer received for this delivery.

    Body:
        otp: "123456"

    Each rider can only verify deliveries assigned to
    them.
    """

    rider = request.user

    if not getattr(rider, "is_authenticated", False):

        return JsonResponse(
            {"error": "Authentication required."},
            status=401,
        )

    try:

        delivery = (
            Delivery.objects
            .only("id", "fulfillment_id")
            .get(pk=delivery_id)
        )

    except Delivery.DoesNotExist:

        return JsonResponse(
            {"error": "Delivery not found."},
            status=404,
        )

    otp = (request.POST.get("otp") or "").strip()

    if not otp:

        return JsonResponse(
            {"error": "OTP is required."},
            status=400,
        )

    try:

        OrderFulfillmentService.verify_delivery_otp(
            rider=rider,
            delivery=delivery,
            otp=otp,
        )

    except ValueError as exc:

        return JsonResponse(
            {"error": str(exc)},
            status=400,
        )

    except Exception:

        logger.exception(
            "OTP verification failed for delivery %s.",
            delivery_id,
        )

        return JsonResponse(
            {"error": "Verification failed."},
            status=500,
        )

    return JsonResponse(
        {
            "status": True,
            "message": "Delivery confirmed.",
        },
        status=200,
    )