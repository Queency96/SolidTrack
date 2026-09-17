from rest_framework import serializers

from ..models import ProductCategory


# ============================================================
# Product Category Serializer
# ============================================================

class ProductCategorySerializer(
    serializers.ModelSerializer,
):
    """
    Admin/vendor-facing serializer for ProductCategory.

    Hierarchy information and aggregate counts should be
    supplied by the optimized queryset.

    Expected queryset annotations:

        _annotated_has_children
        _annotated_product_count
        _annotated_active_product_count

    This serializer does not perform hierarchy traversal or
    aggregate database queries.
    """

    # ========================================================
    # Hierarchy
    # ========================================================

    is_root = serializers.ReadOnlyField()

    is_subcategory = serializers.ReadOnlyField()

    has_children = serializers.BooleanField(
        source="_annotated_has_children",
        read_only=True,
    )

    # ========================================================
    # Product Counts
    # ========================================================

    product_count = serializers.IntegerField(
        source="_annotated_product_count",
        read_only=True,
    )

    active_product_count = serializers.IntegerField(
        source="_annotated_active_product_count",
        read_only=True,
    )

    # ========================================================
    # Meta
    # ========================================================

    class Meta:
        model = ProductCategory

        fields = (
            # ------------------------------------------------
            # Identity
            # ------------------------------------------------

            "id",
            "name",
            "slug",

            # ------------------------------------------------
            # Hierarchy
            # ------------------------------------------------

            "parent",

            # ------------------------------------------------
            # Content
            # ------------------------------------------------

            "description",
            "image",

            # ------------------------------------------------
            # Ordering
            # ------------------------------------------------

            "sort_order",

            # ------------------------------------------------
            # Status
            # ------------------------------------------------

            "is_active",

            # ------------------------------------------------
            # Computed hierarchy
            # ------------------------------------------------

            "is_root",
            "is_subcategory",
            "has_children",

            # ------------------------------------------------
            # Product statistics
            # ------------------------------------------------

            "product_count",
            "active_product_count",

            # ------------------------------------------------
            # Timestamps
            # ------------------------------------------------

            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "is_root",
            "is_subcategory",
            "has_children",
            "product_count",
            "active_product_count",
            "created_at",
            "updated_at",
        )


# ============================================================
# Public Product Category Serializer
# ============================================================

class PublicProductCategorySerializer(
    serializers.ModelSerializer,
):
    """
    Read-only public representation of ProductCategory.

    All hierarchy and aggregate information is expected to be
    calculated by the queryset before serialization.
    """

    # ========================================================
    # Hierarchy
    # ========================================================

    is_root = serializers.ReadOnlyField()

    is_subcategory = serializers.ReadOnlyField()

    has_children = serializers.BooleanField(
        source="_annotated_has_children",
        read_only=True,
    )

    # ========================================================
    # Product Counts
    # ========================================================

    product_count = serializers.IntegerField(
        source="_annotated_product_count",
        read_only=True,
    )

    active_product_count = serializers.IntegerField(
        source="_annotated_active_product_count",
        read_only=True,
    )

    # ========================================================
    # Root Category
    # ========================================================

    root_category_id = serializers.SerializerMethodField()

    # ========================================================
    # Meta
    # ========================================================

    class Meta:
        model = ProductCategory

        fields = (
            # ------------------------------------------------
            # Identity
            # ------------------------------------------------

            "id",
            "name",
            "slug",

            # ------------------------------------------------
            # Hierarchy
            # ------------------------------------------------

            "parent",

            # ------------------------------------------------
            # Content
            # ------------------------------------------------

            "description",
            "image",

            # ------------------------------------------------
            # Ordering
            # ------------------------------------------------

            "sort_order",

            # ------------------------------------------------
            # Hierarchy state
            # ------------------------------------------------

            "is_root",
            "is_subcategory",
            "has_children",

            # ------------------------------------------------
            # Product statistics
            # ------------------------------------------------

            "product_count",
            "active_product_count",

            # ------------------------------------------------
            # Root category
            # ------------------------------------------------

            "root_category_id",
        )

        read_only_fields = fields

    # ========================================================
    # Root Category
    # ========================================================

    def get_root_category_id(self, obj):
        """
        Return the precomputed root category ID.

        The queryset should attach:

            _annotated_root_category_id

        This prevents the serializer from recursively walking
        parent relationships.
        """

        return getattr(
            obj,
            "_annotated_root_category_id",
            None,
        )