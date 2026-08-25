from django.db.models import Q

from rest_framework import generics
from rest_framework.permissions import IsAdminUser
from rest_framework.filters import (
    SearchFilter,
    OrderingFilter,
)

from ..models import ProductCategory

from ..serializers.product_category import (
    ProductCategorySerializer,
    PublicProductCategorySerializer,
)


# ==================================================
# Public Category List
# ==================================================

class PublicProductCategoryListView(
    generics.ListAPIView,
):
    """
    Return active product categories available
    to marketplace customers.
    """

    serializer_class = PublicProductCategorySerializer

    filter_backends = [
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "name",
        "description",
    ]

    ordering_fields = [
        "name",
        "sort_order",
        "created_at",
    ]

    ordering = [
        "sort_order",
        "name",
    ]

    def get_queryset(self):

        return (
            ProductCategory.objects
            .filter(
                is_active=True,
            )
            .select_related(
                "parent",
            )
        )


# ==================================================
# Public Category Detail
# ==================================================

class PublicProductCategoryDetailView(
    generics.RetrieveAPIView,
):
    """
    Return a single active product category.
    """

    serializer_class = PublicProductCategorySerializer

    lookup_field = "slug"

    def get_queryset(self):

        return (
            ProductCategory.objects
            .filter(
                is_active=True,
            )
            .select_related(
                "parent",
            )
        )


# ==================================================
# Admin Category List / Create
# ==================================================

class AdminProductCategoryListCreateView(
    generics.ListCreateAPIView,
):
    """
    Admin endpoint for listing and creating
    product categories.
    """

    permission_classes = [
        IsAdminUser,
    ]

    serializer_class = ProductCategorySerializer

    filter_backends = [
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "name",
        "slug",
        "description",
    ]

    ordering_fields = [
        "name",
        "sort_order",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "sort_order",
        "name",
    ]

    def get_queryset(self):

        return (
            ProductCategory.objects
            .select_related(
                "parent",
            )
        )


# ==================================================
# Admin Category Detail
# ==================================================

class AdminProductCategoryDetailView(
    generics.RetrieveUpdateDestroyAPIView,
):
    """
    Admin endpoint for retrieving, updating,
    and deleting a product category.
    """

    permission_classes = [
        IsAdminUser,
    ]

    serializer_class = ProductCategorySerializer

    lookup_field = "pk"

    def get_queryset(self):

        return (
            ProductCategory.objects
            .select_related(
                "parent",
            )
        )