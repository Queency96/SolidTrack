import logging
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from order.services import PaymentService
from checkout.services.exceptions import (
    InvalidWebhookSignature,
    WebhookPayloadError,
)


logger = logging.getLogger(__name__)


"""
Paystack webhook receiver.

Paystack computes an HMAC-SHA512 signature over the raw
request body and sends it in the `x-paystack-signature`
header. We pass the raw bytes to PaymentService so that
signature verification operates on the exact bytes Paystack
signed — parsing before verification would invalidate the
signature.

Security
--------
- CSRF exemption is required: Paystack cannot send a CSRF
  token. This is safe because the request is authenticated
  by the HMAC signature, not by session cookies.
- The webhook endpoint must be publicly reachable, so it
  also enforces a hard cap on body size to prevent memory
  exhaustion.
- Signature verification is delegated to
  PaymentService.handle_webhook, which raises
  InvalidWebhookSignature on failure.
"""




# Maximum accepted webhook body size (bytes).
# Paystack events are typically well under 100 KB.
MAX_WEBHOOK_BODY_SIZE = 1024 * 1024  # 1 MiB


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """
    Receive and process a Paystack webhook.

    Returns:
        200 — event received (accepted or idempotently
              skipped)
        400 — malformed payload
        401 — invalid signature
        413 — payload too large
        500 — internal processing error
    """

    # --------------------------------------------------
    # Reject oversized bodies.
    # --------------------------------------------------

    content_length = request.META.get("CONTENT_LENGTH")

    if content_length:

        try:
            content_length = int(content_length)

        except (TypeError, ValueError):
            content_length = None

        if (
            content_length is not None
            and content_length > MAX_WEBHOOK_BODY_SIZE
        ):

            logger.warning(
                "Rejected oversized Paystack webhook "
                "(Content-Length=%s).",
                content_length,
            )

            return JsonResponse(
                {"error": "Payload too large."},
                status=413,
            )

    # --------------------------------------------------
    # Content-Type check.
    # --------------------------------------------------

    content_type = request.content_type or ""

    if "application/json" not in content_type.lower():

        logger.warning(
            "Rejected Paystack webhook with "
            "Content-Type=%r.",
            content_type,
        )

        return JsonResponse(
            {"error": "Unsupported content type."},
            status=400,
        )

    # --------------------------------------------------
    # Signature header.
    # --------------------------------------------------

    signature = request.headers.get(
        "x-paystack-signature",
    )

    if not signature:

        logger.warning(
            "Rejected Paystack webhook without signature "
            "header.",
        )

        return JsonResponse(
            {"error": "Missing signature."},
            status=401,
        )

    # --------------------------------------------------
    # Delegate to the service layer.
    #
    # Raw bytes are passed for HMAC verification.
    # --------------------------------------------------

    try:

        PaymentService.handle_webhook(
            payload=request.body,
            signature=signature,
        )

    except InvalidWebhookSignature:

        logger.warning(
            "Rejected Paystack webhook with invalid "
            "signature.",
        )

        return JsonResponse(
            {"error": "Invalid signature."},
            status=401,
        )

    except WebhookPayloadError as exc:

        logger.warning(
            "Rejected malformed Paystack webhook: %s",
            exc,
        )

        return JsonResponse(
            {"error": "Malformed payload."},
            status=400,
        )

    except Exception:

        logger.exception(
            "Unexpected error processing Paystack "
            "webhook.",
        )

        return JsonResponse(
            {"error": "Webhook processing failed."},
            status=500,
        )

    return JsonResponse(
        {"status": True},
        status=200,
    )