from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from order.services import PaymentService


@csrf_exempt
def paystack_webhook(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "error": "Method not allowed."
            },
            status=405,
        )

    signature = request.headers.get(
        "x-paystack-signature"
    )

    try:

        PaymentService.handle_webhook(
            payload=request.body,
            signature=signature,
        )

    except PermissionError:

        return JsonResponse(
            {
                "error": "Invalid signature."
            },
            status=401,
        )

    except Exception:

        # Do not expose internal payment details.
        # Log the exception in production.
        return JsonResponse(
            {
                "error": "Webhook processing failed."
            },
            status=500,
        )

    # Paystack expects a 200 acknowledgement.
    return JsonResponse(
        {
            "status": True,
        },
        status=200,
    )