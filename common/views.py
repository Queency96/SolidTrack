"""
Location endpoints for the customer-facing storefront.

Provides the Nigerian state list used by the frontend state
selector. Includes a per-state product count so the UI can
mute states that have no vendors yet.
"""

from django.core.cache import cache
from django.db.models import Count, Q
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.constant import NIGERIA_STATE_CHOICES

# Lazy import to avoid a circular dependency with vendors app
# at Django startup.
from vendors.models import Product


STATES_CACHE_KEY = "locations:states:with_product_count"
STATES_CACHE_TIMEOUT = 5 * 60  # seconds


class StatesListView(APIView):
    """
    Return all Nigerian states with a count of publicly visible
    products in each state.

    Public. Cached for 5 minutes.

    Response shape:

        {
            "states": [
                {"code": "LA", "name": "Lagos", "product_count": 1204},
                ...
            ]
        }

    `product_count` reflects only products that pass the public
    visibility filters:

        product.is_active = True
        product.is_published = True
        store.is_active = True
        store.is_verified = True
        store.accepting_orders = True
    """

    permission_classes = [AllowAny]

    def get(self, request):
        cached = cache.get(STATES_CACHE_KEY)

        if cached is not None:
            return Response({"states": cached})

        counts_by_code = self._product_counts_by_state_code()

        states = [
            {
                "code": code,
                "name": name,
                "product_count": counts_by_code.get(code, 0),
            }
            for code, name in NIGERIA_STATE_CHOICES
        ]

        cache.set(
            STATES_CACHE_KEY,
            states,
            STATES_CACHE_TIMEOUT,
        )

        return Response({"states": states})

    # ----------------------------------------------------------
    # Counting
    # ----------------------------------------------------------

    @staticmethod
    def _product_counts_by_state_code():
        """
        Return {state_code: product_count} for publicly visible
        products.

        Aggregates by the store's state_code. Stores with an
        empty state_code are excluded — they would not match any
        filter anyway.
        """

        rows = (
            Product.objects
            .filter(
                is_active=True,
                is_published=True,
                store__is_active=True,
                store__is_verified=True,
                store__accepting_orders=True,
            )
            .exclude(store__state_code="")
            .values("store__state_code")
            .annotate(total=Count("id"))
        )

        return {
            row["store__state_code"]: row["total"]
            for row in rows
        }