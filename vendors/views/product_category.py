from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework import generics
from rest_framework.permissions import IsAdminUser
from rest_framework.filters import (
    SearchFilter,
    OrderingFilter,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models import ProductCategory, CategoryOption
from ..serializers.product_category import (
    ProductCategorySerializer,
    PublicProductCategorySerializer,
)
from ..serializers.category_option import CategoryOptionSimpleSerializer


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
    permission_classes = [
        AllowAny,
    ]

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
    permission_classes = [
        AllowAny,
    ]

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
# Category Options API
# ==================================================

class CategoryOptionsView(APIView):
    """
    GET:
        Return the category options (option templates)
        for a specific category.
        
        This helps vendors know what options they can
        define when creating products in this category.
    """

    permission_classes = [AllowAny]

    def get(self, request, category_slug):
        try:
            category = ProductCategory.objects.get(
                slug=category_slug,
                is_active=True,
            )
        except ProductCategory.DoesNotExist:
            return Response(
                {"error": "Category not found."},
                status=404,
            )

        # Get all category options (including inherited)
        category_options = CategoryOption.objects.filter(
            category=category,
            is_active=True,
        ).order_by('sort_order', 'name')

        serializer = CategoryOptionSimpleSerializer(
            category_options,
            many=True,
        )

        return Response({
            "category": {
                "id": str(category.id),
                "name": category.name,
                "slug": category.slug,
            },
            "options": serializer.data,
            "count": len(serializer.data),
        })


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