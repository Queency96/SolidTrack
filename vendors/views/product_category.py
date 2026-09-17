from django.db.models import Count, Exists, OuterRef, Q
from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import CategoryOption, ProductCategory
from ..serializers.category_option import CategoryOptionSimpleSerializer
from ..serializers.product_category import (
    ProductCategorySerializer,
    PublicProductCategorySerializer,
)


# ==========================================================
# Category Querysets
# ==========================================================

def get_category_queryset():
    """
    Base ProductCategory queryset used by admin/category APIs.

    Database calculates:

        - product_count
        - active_product_count
        - has_children

    The parent category is loaded with select_related().

    Annotation names intentionally differ from model properties.
    """

    children_queryset = ProductCategory.objects.filter(
        parent_id=OuterRef("pk"),
    )

    return (
        ProductCategory.objects
        .select_related("parent")
        .annotate(
            _annotated_product_count=Count(
                "products",
                distinct=True,
            ),
            _annotated_active_product_count=Count(
                "products",
                filter=Q(
                    products__is_active=True,
                    products__is_published=True,
                ),
                distinct=True,
            ),
            _annotated_has_children=Exists(
                children_queryset,
            ),
        )
        .order_by(
            "sort_order",
            "name",
        )
    )


def get_public_category_queryset():
    """
    Optimized queryset for public category endpoints.

    Only active categories are exposed.

    Product counts represent products that are:

        - active
        - published
    """

    children_queryset = ProductCategory.objects.filter(
        parent_id=OuterRef("pk"),
        is_active=True,
    )

    return (
        ProductCategory.objects
        .filter(
            is_active=True,
        )
        .select_related("parent")
        .annotate(
            _annotated_product_count=Count(
                "products",
                filter=Q(
                    products__is_active=True,
                    products__is_published=True,
                ),
                distinct=True,
            ),
            _annotated_active_product_count=Count(
                "products",
                filter=Q(
                    products__is_active=True,
                    products__is_published=True,
                ),
                distinct=True,
            ),
            _annotated_has_children=Exists(
                children_queryset,
            ),
        )
        .order_by(
            "sort_order",
            "name",
        )
    )


# ==========================================================
# Root Category Resolution
# ==========================================================

def attach_root_category_ids(categories):
    """
    Attach root category IDs to an already-materialized category
    collection.

    The function performs no database queries.

    It follows the parent relationships that were loaded by
    select_related("parent") and resolves the root in memory.

    If the complete hierarchy is not present in the supplied
    collection, the already-loaded parent chain is used.

    A defensive cycle check prevents infinite loops if malformed
    category data exists.
    """

    categories = list(categories)

    if not categories:
        return categories

    resolved_roots = {}

    for category in categories:
        current = category
        visited = set()

        while current.parent_id:
            current_id = current.pk

            if current_id in visited:
                # Defensive protection against malformed
                # cyclic category data.
                break

            visited.add(current_id)

            parent = getattr(current, "parent", None)

            if parent is None:
                break

            current = parent

        if current.pk not in visited:
            resolved_roots[category.pk] = current.pk
        else:
            # Defensive fallback for a malformed cycle.
            resolved_roots[category.pk] = category.pk

    for category in categories:
        setattr(
            category,
            "_annotated_root_category_id",
            resolved_roots.get(category.pk),
        )

    return categories


# ==========================================================
# Public Category List
# ==========================================================

class PublicProductCategoryListView(generics.ListAPIView):
    """
    Public list of active product categories.
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
        return get_public_category_queryset()

    def list(self, request, *args, **kwargs):
        """
        Materialize once so root category IDs can be attached
        without serializer N+1 queries.
        """

        queryset = self.filter_queryset(
            self.get_queryset()
        )

        categories = list(queryset)

        attach_root_category_ids(categories)

        serializer = self.get_serializer(
            categories,
            many=True,
        )

        return Response(serializer.data)


# ==========================================================
# Public Category Detail
# ==========================================================

class PublicProductCategoryDetailView(
    generics.RetrieveAPIView
):
    """
    Public detail endpoint for an active category.
    """

    serializer_class = PublicProductCategorySerializer

    permission_classes = [
        AllowAny,
    ]

    lookup_field = "slug"

    def get_queryset(self):
        return get_public_category_queryset()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        attach_root_category_ids(
            [instance],
        )

        serializer = self.get_serializer(instance)

        return Response(serializer.data)


# ==========================================================
# Public Category Options
# ==========================================================

class CategoryOptionsView(APIView):
    """
    Return active options belonging to an active category.

    Example:

        GET /categories/<slug>/options/
    """

    permission_classes = [
        AllowAny,
    ]

    def get(self, request, category_slug):
        category = (
            ProductCategory.objects
            .filter(
                slug=category_slug,
                is_active=True,
            )
            .only(
                "id",
                "name",
                "slug",
            )
            .first()
        )

        if category is None:
            return Response(
                {
                    "detail": "Category not found.",
                },
                status=404,
            )

        category_options = (
            CategoryOption.objects
            .filter(
                category_id=category.pk,
                is_active=True,
            )
            .only(
                "id",
                "name",
                "slug",
                "sort_order",
            )
            .order_by(
                "sort_order",
                "name",
            )
        )

        serializer = CategoryOptionSimpleSerializer(
            category_options,
            many=True,
        )

        return Response(
            {
                "category": {
                    "id": str(category.id),
                    "name": category.name,
                    "slug": category.slug,
                },
                "options": serializer.data,
                "count": len(serializer.data),
            }
        )


# ==========================================================
# Admin Category List / Create
# ==========================================================

class AdminProductCategoryListCreateView(
    generics.ListCreateAPIView
):
    """
    Admin category list and creation endpoint.
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
        return get_category_queryset()

    def perform_create(self, serializer):
        """
        Keep creation through the serializer.

        This method is intentionally thin because category
        creation does not require additional ownership logic.
        """

        serializer.save()


# ==========================================================
# Admin Category Detail
# ==========================================================

class AdminProductCategoryDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    """
    Admin category retrieve/update/delete endpoint.
    """

    permission_classes = [
        IsAdminUser,
    ]

    serializer_class = ProductCategorySerializer

    lookup_field = "pk"

    def get_queryset(self):
        return get_category_queryset()

    def perform_update(self, serializer):
        serializer.save()