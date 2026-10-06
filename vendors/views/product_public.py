from django.db.models import Prefetch, Q
from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from common.constant import STATE_CODE_TO_NAME
from common.pagination import StandardPageNumberPagination
from common.utils.geo import resolve_browse_state

from vendors.models import (
    Product,
    ProductImage,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
    ProductVariantImage,
    ProductVariantOptionValue,
)

from vendors.serializers.product import (
    PublicProductDetailSerializer,
    PublicProductSerializer,
)


# ==========================================================
# Shared queryset mixin
# ==========================================================

class PublicProductQuerySetMixin:
    """
    Shared queryset architecture for the customer-facing
    product endpoints.
    """

    PUBLIC_PRODUCT_FILTERS = {
        "is_active": True,
        "is_published": True,
        "store__is_active": True,
        "store__is_verified": True,
        "store__accepting_orders": True,
    }

    @staticmethod
    def parse_boolean(value):
        if value is None:
            return None

        value = str(value).strip().lower()

        if value in {"1", "true", "yes", "on"}:
            return True
        if value in {"0", "false", "no", "off"}:
            return False

        return None

    def get_base_public_queryset(self):
        return (
            Product.objects
            .filter(**self.PUBLIC_PRODUCT_FILTERS)
            .select_related("vendor", "store", "category")
        )

    @staticmethod
    def get_public_product_images_queryset():
        return (
            ProductImage.objects
            .filter(is_active=True)
            .order_by("display_order", "created_at")
        )

    @staticmethod
    def get_public_option_values_queryset():
        return (
            ProductOptionValue.objects
            .filter(is_active=True)
            .order_by("sort_order", "name")
        )

    @classmethod
    def get_public_options_queryset(cls):
        return (
            ProductOption.objects
            .filter(is_active=True)
            .prefetch_related(
                Prefetch(
                    "values",
                    queryset=cls.get_public_option_values_queryset(),
                    to_attr="_prefetched_active_values",
                ),
            )
            .order_by("sort_order", "name")
        )

    @staticmethod
    def get_public_variant_images_queryset():
        return (
            ProductVariantImage.objects
            .filter(is_active=True)
            .order_by("-is_primary", "display_order", "created_at")
        )

    @staticmethod
    def get_public_variant_option_links_queryset():
        return (
            ProductVariantOptionValue.objects
            .select_related("option_value", "option_value__option")
            .order_by(
                "option_value__option__sort_order",
                "option_value__option__name",
                "option_value__sort_order",
                "option_value__name",
            )
        )

    @classmethod
    def get_public_variants_queryset(cls):
        return (
            ProductVariant.objects
            .filter(is_active=True)
            .prefetch_related(
                Prefetch(
                    "variant_option_values",
                    queryset=cls.get_public_variant_option_links_queryset(),
                    to_attr="_prefetched_variant_option_links",
                ),
                Prefetch(
                    "images",
                    queryset=cls.get_public_variant_images_queryset(),
                    to_attr="_prefetched_variant_images",
                ),
            )
            .order_by("sort_order", "name", "created_at")
        )

    def get_public_list_queryset(self):
        return (
            self.get_base_public_queryset()
            .prefetch_related(
                Prefetch(
                    "images",
                    queryset=self.get_public_product_images_queryset(),
                    to_attr="_prefetched_product_images",
                ),
            )
        )

    def get_public_detail_queryset(self):
        return (
            self.get_base_public_queryset()
            .prefetch_related(
                Prefetch(
                    "images",
                    queryset=self.get_public_product_images_queryset(),
                    to_attr="_prefetched_product_images",
                ),
                Prefetch(
                    "options",
                    queryset=self.get_public_options_queryset(),
                    to_attr="_prefetched_options",
                ),
                Prefetch(
                    "variants",
                    queryset=self.get_public_variants_queryset(),
                    to_attr="_prefetched_variants",
                ),
            )
        )


# ==========================================================
# Common list-filter logic
# ==========================================================

class _ProductFilterMixin:
    """
    Shared query-param filtering for both list endpoints.
    """

    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = [
        "name", "slug", "sku", "short_description", "description",
        "vendor__company_name", "store__name", "category__name",
    ]

    ordering_fields = [
        "name", "price", "compare_at_price", "sort_order", "created_at",
    ]

    ordering = ["sort_order", "-created_at"]

    def apply_common_filters(self, queryset, params):
        in_stock = self.parse_boolean(params.get("in_stock"))

        if in_stock is True:
            queryset = queryset.filter(
                Q(track_inventory=False) | Q(stock_quantity__gt=0)
            )
        elif in_stock is False:
            queryset = queryset.filter(
                track_inventory=True, stock_quantity__lte=0,
            )

        featured = self.parse_boolean(params.get("featured"))

        if featured is not None:
            queryset = queryset.filter(is_featured=featured)

        category = params.get("category")
        if category:
            queryset = queryset.filter(category__slug=category)

        store = params.get("store")
        if store:
            queryset = queryset.filter(store__slug=store)

        vendor = params.get("vendor")
        if vendor:
            queryset = queryset.filter(vendor_id=vendor)

        return queryset


# ==========================================================
# GUEST LIST — no state filter
# ==========================================================

class PublicProductListView(
    _ProductFilterMixin,
    PublicProductQuerySetMixin,
    generics.ListAPIView,
):
    """
    Guest product listing.

    No state filtering. Returns the full public catalogue.

    Pagination
    ----------
    ?page=<int>          Page number (1-based).
    ?page_size=<int>     Optional override, capped at 100.
    """

    serializer_class = PublicProductSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        queryset = self.get_public_list_queryset()
        return self.apply_common_filters(
            queryset,
            self.request.query_params,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(
            page if page is not None else queryset,
            many=True,
        )

        meta = {
            "state_code": None,
            "state_name": None,
            "state_source": "guest",
            "has_products_in_state": True,
        }

        if page is not None:
            response = self.get_paginated_response(serializer.data)
            response.data["meta"] = meta
            return response

        return Response({"results": serializer.data, "meta": meta})


# ==========================================================
# AUTHENTICATED LIST — state-filtered
# ==========================================================

class MyStateProductListView(
    _ProductFilterMixin,
    PublicProductQuerySetMixin,
    generics.ListAPIView,
):
    """
    Authenticated product listing with state scoping.

    State resolution precedence (via resolve_browse_state):

        1. ?state=<code|name>          explicit override
        2. IPStateMapping              learned (>=5 verified votes)
        3. GeoLite2                    offline
        4. FreeIPAPI                   HTTPS provider
        5. ip-api.com                  HTTP provider
        6. User.state                  profile fallback
        7. None                        frontend prompts

    Pagination
    ----------
    ?page=<int>          Page number (1-based).
    ?page_size=<int>     Optional override, capped at 100.
    """

    serializer_class = PublicProductSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        queryset = self.get_public_list_queryset()

        state_code, _ = resolve_browse_state(self.request)

        if state_code:
            queryset = queryset.filter(store__state_code=state_code)

        return self.apply_common_filters(
            queryset,
            self.request.query_params,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(
            page if page is not None else queryset,
            many=True,
        )

        state_code, state_source = resolve_browse_state(request)

        # Total matching the *filtered* queryset, not just this page.
        result_count = (
            page.paginator.count
            if page is not None
            else queryset.count()
        )

        meta = {
            "state_code": state_code,
            "state_name": STATE_CODE_TO_NAME.get(state_code),
            "state_source": state_source,
            "has_products_in_state": bool(state_code and result_count > 0),
            "state_override_url": (
                f"{request.path}?state=<state_code>"
            ),
        }

        if page is not None:
            response = self.get_paginated_response(serializer.data)
            response.data["meta"] = meta
            return response

        return Response({"results": serializer.data, "meta": meta})


# ==========================================================
# DETAIL — shared by both audiences
# ==========================================================

class PublicProductDetailView(
    PublicProductQuerySetMixin,
    generics.RetrieveAPIView,
):
    """
    Product detail. Shared by guest and authenticated callers.

    Not state-filtered. When the caller is authenticated and the
    product's store state differs from the resolved browse state,
    the response carries a `state_warning` block.
    """

    serializer_class = PublicProductDetailSerializer
    permission_classes = [AllowAny]

    lookup_field = "pk"
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return self.get_public_detail_queryset()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = dict(self.get_serializer(instance).data)

        if request.user.is_authenticated:
            browse_state_code, _ = resolve_browse_state(request)
            store_state_code = (
                getattr(instance.store, "state_code", "") or None
            )

            if (
                browse_state_code
                and store_state_code
                and browse_state_code != store_state_code
            ):
                data["state_warning"] = {
                    "message": (
                        f"This product is in "
                        f"{STATE_CODE_TO_NAME.get(store_state_code, store_state_code)}, "
                        f"not your state "
                        f"({STATE_CODE_TO_NAME.get(browse_state_code, browse_state_code)}). "
                        "Delivery may not be available."
                    ),
                    "product_state_code": store_state_code,
                    "product_state_name": STATE_CODE_TO_NAME.get(store_state_code),
                    "browse_state_code": browse_state_code,
                    "browse_state_name": STATE_CODE_TO_NAME.get(browse_state_code),
                }

        return Response(data)