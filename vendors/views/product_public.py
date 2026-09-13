from django.db.models import Q
from rest_framework import generics
from rest_framework.filters import (
    OrderingFilter,
    SearchFilter,
)
from rest_framework.permissions import AllowAny

from vendors.models.product import Product
from vendors.serializers.product import (
    PublicProductDetailSerializer,
    PublicProductSerializer,
)


class PublicProductListView(
    generics.ListAPIView,
):
    """
    Public storefront product listing.

    Returns products which are currently purchasable
    by marketplace customers:

        - product is active and published
        - product is in stock (unless inventory is not
          tracked)
        - the store is active, verified and accepting
          orders

    Supports searching and ordering, plus optional
    filtering via query parameters:

        ?category=<slug>
        ?store=<slug>
        ?vendor=<uuid>
        ?featured=true|false
        ?in_stock=true|false
    """

    serializer_class = PublicProductSerializer

    permission_classes = [
        AllowAny,
    ]

    filter_backends = [
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "name",
        "slug",
        "sku",
        "short_description",
        "description",
        "vendor__company_name",
        "store__name",
        "category__name",
    ]

    ordering_fields = [
        "name",
        "price",
        "compare_at_price",
        "sort_order",
        "created_at",
    ]

    ordering = [
        "sort_order",
        "-created_at",
    ]

    def get_queryset(self):

        queryset = (
            Product.objects
            .filter(
                is_active=True,
                is_published=True,
                store__is_active=True,
                store__is_verified=True,
                store__accepting_orders=True,
            )
            .select_related(
                "vendor",
                "store",
                "category",
            )
            .prefetch_related(
                "images",
            )
        )

        params = self.request.query_params

        # ----------------------------------------------
        # in_stock filter
        # ----------------------------------------------

        in_stock = params.get("in_stock")

        if in_stock is not None:

            if in_stock.lower() in {
                "1",
                "true",
                "yes",
            }:

                queryset = queryset.filter(
                    Q(track_inventory=False)
                    | Q(stock_quantity__gt=0)
                )

        # ----------------------------------------------
        # featured filter
        # ----------------------------------------------

        featured = params.get("featured")

        if featured is not None:

            queryset = queryset.filter(
                is_featured=(
                    featured.lower()
                    in {
                        "1",
                        "true",
                        "yes",
                    }
                )
            )

        # ----------------------------------------------
        # category filter (by slug)
        # ----------------------------------------------

        category = params.get("category")

        if category:

            queryset = queryset.filter(
                category__slug=category
            )

        # ----------------------------------------------
        # store filter (by slug)
        # ----------------------------------------------

        store = params.get("store")

        if store:

            queryset = queryset.filter(
                store__slug=store
            )

        # ----------------------------------------------
        # vendor filter (by uuid)
        # ----------------------------------------------

        vendor = params.get("vendor")

        if vendor:

            queryset = queryset.filter(
                vendor_id=vendor
            )

        return queryset


class PublicProductDetailView(
    generics.RetrieveAPIView,
):
    """
    Public storefront product detail.

    Returns the full buyer-facing payload for one
    product, including its images and variants.
    """

    serializer_class = PublicProductDetailSerializer

    permission_classes = [
        AllowAny,
    ]

    lookup_field = "pk"

    lookup_url_kwarg = "pk"

    def get_queryset(self):

        return (
            Product.objects
            .filter(
                is_active=True,
                is_published=True,
                store__is_active=True,
                store__is_verified=True,
                store__accepting_orders=True,
            )
            .select_related(
                "vendor",
                "store",
                "category",
            )
            .prefetch_related(
                "images",
                (
                    "variants__variant_option_values"
                    "__option_value__option"
                ),
            )
        )