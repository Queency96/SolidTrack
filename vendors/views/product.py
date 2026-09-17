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
    Shared queryset architecture for public product endpoints.

    ============================================================
    PUBLIC VISIBILITY
    ============================================================

    A product is publicly visible only when:

        product.is_active = True
        product.is_published = True
        store.is_active = True
        store.is_verified = True
        store.accepting_orders = True

    ============================================================
    LIST
    ============================================================

    Product
        ├── Vendor
        ├── Store
        ├── Category
        └── active ProductImages

    Variants and options are intentionally NOT loaded.

    ============================================================
    DETAIL
    ============================================================

    Product
        ├── Vendor
        ├── Store
        ├── Category
        ├── active ProductImages
        ├── active ProductOptions
        │      └── active ProductOptionValues
        └── active ProductVariants
               ├── ProductVariantOptionValues
               │      └── ProductOptionValue
               │             └── ProductOption
               └── active ProductVariantImages

    The queryset uses `to_attr` for nested collections so the
    public serializers can consume prefetched data without
    triggering additional database queries.
    """

    PUBLIC_PRODUCT_FILTERS = {
        "is_active": True,
        "is_published": True,
        "store__is_active": True,
        "store__is_verified": True,
        "store__accepting_orders": True,
    }

    # ============================================================
    # Boolean Parsing
    # ============================================================

    @staticmethod
    def parse_boolean(value):
        """
        Convert common query-string boolean values.

        Returns:
            True
            False
            None
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

    # ============================================================
    # Base Product Queryset
    # ============================================================

    def get_base_public_queryset(self):
        """
        Return the base queryset shared by public list and detail
        endpoints.

        Vendor, store, and category are loaded using select_related()
        because they are single-valued relationships.
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

    # ============================================================
    # Product Images
    # ============================================================

    @staticmethod
    def get_public_product_images_queryset():
        """
        Active product images only.
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

    # ============================================================
    # Product Option Values
    # ============================================================

    @staticmethod
    def get_public_option_values_queryset():
        """
        Active option values only.

        Used by the public product-option response.
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

    # ============================================================
    # Product Options
    # ============================================================

    @classmethod
    def get_public_options_queryset(cls):
        """
        Active product options with active option values.

        `_prefetched_active_values` matches the contract used by
        PublicProductOptionSerializer.
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

    # ============================================================
    # Variant Images
    # ============================================================

    @staticmethod
    def get_public_variant_images_queryset():
        """
        Active variant images only.

        Primary images are returned first.
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

    # ============================================================
    # Variant Option Assignments
    # ============================================================

    @staticmethod
    def get_public_variant_option_links_queryset():
        """
        Load variant-option assignments together with their
        option value and parent option.

        select_related() is used because these are ForeignKey
        relationships.
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

    # ============================================================
    # Product Variants
    # ============================================================

    @classmethod
    def get_public_variants_queryset(cls):
        """
        Active product variants with:

            - selected option values
            - active variant images

        `_prefetched_variant_option_links` and
        `_prefetched_variant_images` match the public
        ProductVariantSerializer implementation.
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
                "created_at",
            )
        )

    # ============================================================
    # Public LIST Queryset
    # ============================================================

    def get_public_list_queryset(self):
        """
        Lightweight queryset for product-card/list responses.

        Deliberately does NOT load:

            - ProductOptions
            - ProductOptionValues
            - ProductVariants
            - ProductVariantOptionValues
            - ProductVariantImages
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

    # ============================================================
    # Public DETAIL Queryset
    # ============================================================

    def get_public_detail_queryset(self):
        """
        Full optimized queryset for a public product detail page.
        """

        return (
            self.get_base_public_queryset()
            .prefetch_related(
                # ------------------------------------------------
                # Product images
                # ------------------------------------------------
                Prefetch(
                    "images",
                    queryset=self.get_public_product_images_queryset(),
                    to_attr="_prefetched_product_images",
                ),

                # ------------------------------------------------
                # Product options + active values
                # ------------------------------------------------
                Prefetch(
                    "options",
                    queryset=self.get_public_options_queryset(),
                    to_attr="_prefetched_options",
                ),

                # ------------------------------------------------
                # Product variants
                # ------------------------------------------------
                Prefetch(
                    "variants",
                    queryset=self.get_public_variants_queryset(),
                    to_attr="_prefetched_variants",
                ),
            )
        )


class PublicProductListView(
    PublicProductQuerySetMixin,
    generics.ListAPIView,
):
    """
    Public product listing.

    Examples:

        GET /products/

        GET /products/?search=iphone

        GET /products/?category=smartphones

        GET /products/?store=ikeja-store

        GET /products/?vendor=<vendor-id>

        GET /products/?featured=true

        GET /products/?in_stock=true

        GET /products/?ordering=-price
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

    # ============================================================
    # Queryset
    # ============================================================

    def get_queryset(self):
        queryset = self.get_public_list_queryset()

        params = self.request.query_params

        # ========================================================
        # IN STOCK
        # ========================================================

        in_stock = self.parse_boolean(
            params.get("in_stock"),
        )

        if in_stock is True:
            queryset = queryset.filter(
                Q(track_inventory=False)
                | Q(stock_quantity__gt=0)
            )

        elif in_stock is False:
            queryset = queryset.filter(
                track_inventory=True,
                stock_quantity__lte=0,
            )

        # ========================================================
        # FEATURED
        # ========================================================

        featured = self.parse_boolean(
            params.get("featured"),
        )

        if featured is not None:
            queryset = queryset.filter(
                is_featured=featured,
            )

        # ========================================================
        # CATEGORY
        # ========================================================

        category = params.get("category")

        if category:
            queryset = queryset.filter(
                category__slug=category,
            )

        # ========================================================
        # STORE
        # ========================================================

        store = params.get("store")

        if store:
            queryset = queryset.filter(
                store__slug=store,
            )

        # ========================================================
        # VENDOR
        # ========================================================

        vendor = params.get("vendor")

        if vendor:
            queryset = queryset.filter(
                vendor_id=vendor,
            )

        return queryset


class PublicProductDetailView(
    PublicProductQuerySetMixin,
    generics.RetrieveAPIView,
):
    """
    Public product detail.

    Loads the complete publicly visible product structure required
    by the product detail page.
    """

    serializer_class = PublicProductDetailSerializer

    permission_classes = [
        AllowAny,
    ]

    lookup_field = "pk"
    lookup_url_kwarg = "pk"

    # ============================================================
    # Queryset
    # ============================================================

    def get_queryset(self):
        return self.get_public_detail_queryset()