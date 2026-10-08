"""
Service-layer exceptions for order processing.
"""


class PaymentServiceError(Exception):
    """
    Base class for payment-service errors.
    """


class InvalidWebhookSignature(PaymentServiceError):
    """
    Raised when a webhook's signature does not match the
    HMAC computed over the raw request body.
    """


class WebhookPayloadError(PaymentServiceError):
    """
    Raised when a webhook payload is structurally invalid:
    malformed JSON, missing required fields, unknown event
    type, etc.
    """


class PaymentProviderError(PaymentServiceError):
    """
    Raised when Paystack returns an error response.
    """


class PaymentProviderTimeout(PaymentProviderError):
    """
    Raised when a Paystack request times out after retries.
    """


class UnsupportedPaymentProvider(PaymentServiceError):
    """
    Raised when a webhook arrives for a provider we do not
    know how to handle.
    """