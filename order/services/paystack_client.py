"""
Thin HTTP client for the Paystack API.

Handles authentication, timeouts, retries, and error
translation. All outbound calls go through this class so
that retry policy, logging, and error shapes are consistent.

Reference: https://paystack.com/docs/api/
"""

import logging

import requests

from django.conf import settings

from .exceptions import (
    PaymentProviderError,
    PaymentProviderTimeout,
)


logger = logging.getLogger(__name__)


class PaystackClient:
    """
    Minimal Paystack REST client.

    Only the endpoints this project needs are wrapped.
    """

    BASE_URL = "https://api.paystack.co"

    # Default timeout applies to both connect and read.
    DEFAULT_TIMEOUT = 15

    # Retry budget for idempotent GETs and safe POSTs.
    DEFAULT_RETRIES = 2

    # ==================================================
    # Public API
    # ==================================================

    @classmethod
    def initialize_transaction(
        cls,
        *,
        email,
        amount_kobo,
        reference,
        callback_url=None,
        metadata=None,
    ):
        """
        Initialize a card / bank transfer payment.

        amount_kobo is the amount in the smallest currency
        unit (kobo for NGN).
        """

        payload = {
            "email": email,
            "amount": int(amount_kobo),
            "reference": reference,
            "currency": "NGN",
        }

        if callback_url:
            payload["callback_url"] = callback_url

        if metadata:
            payload["metadata"] = metadata

        return cls._post(
            "/transaction/initialize",
            payload,
        )

    # ==================================================

    @classmethod
    def verify_transaction(cls, *, reference):
        """
        Verify a completed transaction by reference.

        Used as a backup for the webhook (e.g. when the
        client closes the browser before Paystack's
        callback arrives).
        """

        return cls._get(f"/transaction/verify/{reference}")

    # ==================================================

    @classmethod
    def create_dedicated_account(
        cls,
        *,
        customer_email,
        first_name,
        last_name,
        phone,
        preferred_bank="paystack-titan",
        metadata=None,
    ):
        """
        Create a Dedicated Virtual Account (DVA).

        preferred_bank is one of the banks Paystack
        supports for DVAs. "paystack-titan" settles
        fastest.
        """

        payload = {
            "email": customer_email,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "preferred_bank": preferred_bank,
            "country": "NG",
        }

        if metadata:
            payload["metadata"] = metadata

        return cls._post(
            "/dedicated_account",
            payload,
        )

    # ==================================================

    @classmethod
    def get_dedicated_account(cls, *, account_id):
        """
        Fetch an existing DVA by its Paystack ID.
        """

        return cls._get(f"/dedicated_account/{account_id}")

    # ==================================================
    # HTTP primitives
    # ==================================================

    @classmethod
    def _get(cls, path):
        return cls._request("GET", path)

    @classmethod
    def _post(cls, path, payload):
        return cls._request("POST", path, payload)

    # ==================================================

    @classmethod
    def _request(cls, method, path, payload=None):
        """
        Execute an HTTP request against Paystack.

        Retries on connection errors and 5xx responses.
        Does not retry on 4xx — those are deterministic
        client errors.
        """

        url = f"{cls.BASE_URL}{path}"
        headers = cls._build_headers()

        last_exception = None

        for attempt in range(cls.DEFAULT_RETRIES + 1):

            try:

                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    json=payload,
                    timeout=cls.DEFAULT_TIMEOUT,
                )

            except requests.Timeout as exc:

                last_exception = exc

                logger.warning(
                    "Paystack %s %s timed out (attempt %s).",
                    method,
                    path,
                    attempt + 1,
                )

                continue

            except requests.ConnectionError as exc:

                last_exception = exc

                logger.warning(
                    "Paystack %s %s connection error "
                    "(attempt %s).",
                    method,
                    path,
                    attempt + 1,
                )

                continue

            # ----------------------------------------------
            # Retry on 5xx.
            # ----------------------------------------------

            if 500 <= response.status_code < 600:

                last_exception = PaymentProviderError(
                    f"Paystack returned {response.status_code}."
                )

                logger.warning(
                    "Paystack %s %s returned %s "
                    "(attempt %s).",
                    method,
                    path,
                    response.status_code,
                    attempt + 1,
                )

                continue

            return cls._parse_response(response)

        # --------------------------------------------------
        # Retries exhausted.
        # --------------------------------------------------

        if isinstance(last_exception, requests.Timeout):

            raise PaymentProviderTimeout(
                "Paystack request timed out."
            ) from last_exception

        raise PaymentProviderError(
            "Paystack request failed after retries."
        ) from last_exception

    # ==================================================

    @staticmethod
    def _build_headers():

        secret = getattr(
            settings,
            "PAYSTACK_SECRET_KEY",
            "",
        )

        if not secret:

            raise PaymentProviderError(
                "PAYSTACK_SECRET_KEY is not configured."
            )

        return {
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ==================================================

    @staticmethod
    def _parse_response(response):
        """
        Parse a Paystack response into a dict.

        Paystack responses always have:

            {
                "status": bool,
                "message": str,
                "data": dict | list | None,
            }

        We return the whole body so callers can access
        `status` and `message`; the DVA generator extracts
        `data`.
        """

        try:
            body = response.json()

        except ValueError as exc:

            raise PaymentProviderError(
                f"Paystack returned non-JSON "
                f"(status={response.status_code})."
            ) from exc

        if response.status_code >= 400:

            message = body.get("message") or (
                f"Paystack error {response.status_code}."
            )

            raise PaymentProviderError(message)

        if not body.get("status"):

            raise PaymentProviderError(
                body.get("message")
                or "Paystack reported failure."
            )

        return body