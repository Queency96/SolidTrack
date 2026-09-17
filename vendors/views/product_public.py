from django.db.models import Prefetch, Q
from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny

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


class PublicProductQuerySetMixin:
    """
    Shared queryset logic for publicly visible products.

    List endpoint:
        Loads only data required by product-card responses.

    Detail endpoint:
        Loads the complete publicly visible product structure:

            Product
                ├── ProductImage
                ├── ProductOption
                │     └── ProductOptionValue
                └── ProductVariant
                      ├── ProductVariantOptionValue
                      └── ProductVariantImage

    All public querysets enforce the same visibility rules.
    """

    PUBLIC_PRODUCT_FILTERS = {
        "is_active": True,
        "is_published": True,
        "store__is_active": True,
        "store__is_verified": True,
        "store__accepting_orders": True,
    }

    # ==========================================================
    # Boolean Parsing
    # ==========================================================

    @staticmethod
    def parse_boolean(value):
        """
        Parse common boolean query parameter values.

        Returns:
            True
            False
            None for missing/invalid values
        """

        if value is None:
            return None

        value = str(value).strip().lower()

        if value in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return True

        if value in {
            "0",
            "false",
            "no",
            "off",
        }:
            return False

        return None

    # ==========================================================
    # Base Public Queryset
    # ==========================================================

    def get_base_public_queryset(self):
        """
        Base visibility queryset shared by public list/detail
        endpoints.
        """

        return (
            Product.objects
            .filter(
                **self.PUBLIC_PRODUCT_FILTERS,
            )
            .select_related(
                "vendor",
                "store",
                "category",
            )
        )

    # ==========================================================
    # Public Product Images
    # ==========================================================

    @staticmethod
    def get_public_product_images_queryset():
        """
        Active product images in gallery order.
        """

        return (
            ProductImage.objects
            .filter(
                is_active=True,
            )
            .order_by(
                "display_order",
                "created_at",
            )
        )

    # ==========================================================
    # Public Variant Images
    # ==========================================================

    @staticmethod
    def get_public_variant_images_queryset():
        """
        Active variant images.

        Primary image is returned first, followed by gallery
        ordering.
        """

        return (
            ProductVariantImage.objects
            .filter(
                is_active=True,
            )
            .order_by(
                "-is_primary",
                "display_order",
                "created_at",
            )
        )

    # ==========================================================
    # Public Option Values
    # ==========================================================

    @staticmethod
    def get_public_option_values_queryset():
        """
        Only active option values are exposed publicly.
        """

        return (
            ProductOptionValue.objects
            .filter(
                is_active=True,
            )
            .order_by(
                "sort_order",
                "name",
            )
        )

    # ==========================================================
    # Public Product Options
    # ==========================================================

    @classmethod
    def get_public_options_queryset(cls):
        """
        Return active product options with only active values.

        Results are stored in _prefetched_active_values so the
        serializer can consume them without triggering queries.
        """

        return (
            ProductOption.objects
            .filter(
                active=True,
            )
            .prefetch_related(
                Prefetch(
                    "values",
                    queryset=cls.get_public_option_values_queryset(),
                    to_attr="_prefetched_active_values",
                ),
            )
            .order_by(
                "sort_order",
                "name",
            )
        )

    # ==========================================================
    # Public Variant Option Assignments
    # ==========================================================

    @staticmethod
    def get_public_variant_option_links_queryset():
        """
        Load variant option assignments together with their
        option and option value.

        This matches the ProductVariant serializer's
        _prefetched_variant_option_links contract.
        """

        return (
            ProductVariantOptionValue.objects
            .select_related(
                "option_value",
                "option_value__option",
            )
            .order_by(
                "option_value__option__sort_order",
                "option_value__option__name",
                "option_value__sort_order",
                "option_value__name",
            )
        )

    # ==========================================================
    # Public Variants
    # ==========================================================

    @classmethod
    def get_public_variants_queryset(cls):
        """
        Return active product variants with:

            - option assignments
            - variant images

        Both relationships use to_attr so serializers can
        consume prefetched data without additional queries.
        """

        return (
            ProductVariant.objects
            .filter(
                is_active=True,
            )
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
            .order_by(
                "sort_order",
                "name",
            )
        )

    # ==========================================================
    # Public List Queryset
    # ==========================================================

    def get_public_list_queryset(self):
        """
        Optimized queryset for product-card/list responses.

        Deliberately does NOT load:

            - variants
            - product options
            - option values
            - variant images
        """

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

    # ==========================================================
    # Public Detail Queryset
    # ==========================================================

    def get_public_detail_queryset(self):
        """
        Optimized queryset for product detail responses.

        Loads:

            Product
                ├── active images
                ├── active options
                │     └── active values
                └── active variants
                      ├── option assignments
                      └── active images
        """

        return (
            self.get_base_public_queryset()
            .prefetch_related(
                # --------------------------------------------------
                # Product gallery
                # --------------------------------------------------
                Prefetch(
                    "images",
                    queryset=self.get_public_product_images_queryset(),
                    to_attr="_prefetched_product_images",
                ),

                # --------------------------------------------------
                # Product options
                # --------------------------------------------------
                Prefetch(
                    "options",
                    queryset=self.get_public_options_queryset(),
                    to_attr="_prefetched_options",
                ),

                # --------------------------------------------------
                # Product variants
                # --------------------------------------------------
                Prefetch(
                    "variants",
                    queryset=self.get_public_variants_queryset(),
                    to_attr="_prefetched_variants",
                ),
            )
        )


# ==========================================================
# Public Product List
# ==========================================================

class PublicProductListView(
    PublicProductQuerySetMixin,
    generics.ListAPIView,
):
    """
    Public product listing endpoint.

    Supports:

        - search
        - ordering
        - stock filtering
        - featured filtering
        - category filtering
        - store filtering
        - vendor filtering
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
        queryset = self.get_public_list_queryset()

        params = self.request.query_params

        # ----------------------------------------------------------
        # In-stock filter
        # ----------------------------------------------------------

        in_stock = self.parse_boolean(
            params.get("in_stock"),
        )

        if in_stock is True:
            queryset = queryset.filter(
                Q(track_inventory=False)
                | Q(stock_quantity__gt=0),
            )

        elif in_stock is False:
            queryset = queryset.filter(
                track_inventory=True,
                stock_quantity__lte=0,
            )

        # ----------------------------------------------------------
        # Featured filter
        # ----------------------------------------------------------

        featured = self.parse_boolean(
            params.get("featured"),
        )

        if featured is not None:
            queryset = queryset.filter(
                is_featured=featured,
            )

        # ----------------------------------------------------------
        # Category filter
        # ----------------------------------------------------------

        category = params.get("category")

        if category:
            queryset = queryset.filter(
                category__slug=category,
            )

        # ----------------------------------------------------------
        # Store filter
        # ----------------------------------------------------------

        store = params.get("store")

        if store:
            queryset = queryset.filter(
                store__slug=store,
            )

        # ----------------------------------------------------------
        # Vendor filter
        # ----------------------------------------------------------

        vendor = params.get("vendor")

        if vendor:
            queryset = queryset.filter(
                vendor_id=vendor,
            )

        return queryset


# ==========================================================
# Public Product Detail
# ==========================================================

class PublicProductDetailView(
    PublicProductQuerySetMixin,
    generics.RetrieveAPIView,
):
    """
    Public product detail endpoint.

    Returns the complete publicly visible product structure,
    including variable-product information.
    """

    serializer_class = PublicProductDetailSerializer

    permission_classes = [
        AllowAny,
    ]

    lookup_field = "pk"
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return self.get_public_detail_queryset()