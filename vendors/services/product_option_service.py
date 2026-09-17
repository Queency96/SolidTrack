from django.db import transaction
from django.utils.text import slugify

from vendors.models import (
    Product,
    ProductOption,
    ProductOptionValue,
    CategoryOption,
)


class ProductOptionService:
    """
    Service responsible for product option management.

    Architecture:

        CategoryOption
              │
              ▼
        ProductOption
              │
              ▼
        ProductOptionValue

    CategoryOption is the category-level template.
    ProductOption is the product-specific copy.
    """

    # ============================================================
    # CREATE FROM CATEGORY
    # ============================================================

    @staticmethod
    @transaction.atomic
    def create_options_from_category(product: Product) -> int:
        """
        Create ProductOption records from active CategoryOption
        templates belonging to the product's category.

        Existing product options are preserved.

        Returns:
            Number of newly created ProductOption records.
        """

        if not product.category_id:
            return 0

        category_options = list(
            CategoryOption.objects.filter(
                category_id=product.category_id,
                is_active=True,
            ).order_by(
                "sort_order",
                "name",
            )
        )

        if not category_options:
            return 0

        existing_names = {
            name.casefold()
            for name in ProductOption.objects.filter(
                product_id=product.id,
            ).values_list(
                "name",
                flat=True,
            )
        }

        to_create = []

        for category_option in category_options:

            normalized_name = (
                category_option.name.strip()
            )

            if normalized_name.casefold() in existing_names:
                continue

            to_create.append(
                ProductOption(
                    product_id=product.id,
                    name=normalized_name,
                    slug=category_option.slug,
                    sort_order=category_option.sort_order,
                    is_active=True,
                )
            )

            existing_names.add(
                normalized_name.casefold()
            )

        if not to_create:
            return 0

        ProductOption.objects.bulk_create(
            to_create,
            batch_size=100,
        )

        return len(to_create)

    # ============================================================
    # CATEGORY OPTIONS
    # ============================================================

    @staticmethod
    def get_category_options_for_product(product: Product):
        """
        Return active CategoryOption templates applicable to
        the product category.
        """

        if not product.category_id:
            return CategoryOption.objects.none()

        return (
            CategoryOption.objects
            .filter(
                category_id=product.category_id,
                is_active=True,
            )
            .order_by(
                "sort_order",
                "name",
            )
        )

    # ============================================================
    # PRODUCT TYPE
    # ============================================================

    @staticmethod
    def is_variable_product(product: Product) -> bool:
        """
        A product is variable when at least one variant exists.
        """

        return product.variants.exists()

    @staticmethod
    def is_simple_product(product: Product) -> bool:
        """
        A product is simple when it has no variants.
        """

        return not product.variants.exists()

    @staticmethod
    def get_product_type(product: Product) -> str:
        """
        Return:
            'variable'
            'simple'
        """

        return (
            "variable"
            if product.variants.exists()
            else "simple"
        )

    @staticmethod
    def get_product_type_from_counts(
        *,
        variants_count: int,
    ) -> str:
        """
        Determine product type when the caller already has
        the variant count.

        Avoids another database query.
        """

        return (
            "variable"
            if variants_count > 0
            else "simple"
        )

    # ============================================================
    # PRODUCT OPTIONS
    # ============================================================

    @staticmethod
    def get_product_options(
        product: Product,
        *,
        active_only: bool = True,
        with_values: bool = False,
    ):
        """
        Return product options.

        Args:
            product:
                Product instance.

            active_only:
                Restrict to active options.

            with_values:
                Prefetch option values.
        """

        queryset = ProductOption.objects.filter(
            product_id=product.id,
        )

        if active_only:
            queryset = queryset.filter(
                is_active=True,
            )

        queryset = queryset.order_by(
            "sort_order",
            "name",
        )

        if with_values:
            queryset = queryset.prefetch_related(
                "values",
            )

        return queryset

    # ============================================================
    # OPTION VALUES
    # ============================================================

    @staticmethod
    def get_option_values(
        product_option: ProductOption,
        *,
        active_only: bool = True,
    ):
        """
        Return values belonging to a ProductOption.
        """

        queryset = product_option.values.all()

        if active_only:
            queryset = queryset.filter(
                is_active=True,
            )

        return queryset.order_by(
            "sort_order",
            "name",
        )

    # ============================================================
    # FIND OPTION
    # ============================================================

    @staticmethod
    def get_product_option(
        product: Product,
        name: str,
    ):
        """
        Find a product option case-insensitively.
        """

        if not name:
            return None

        return (
            ProductOption.objects
            .filter(
                product_id=product.id,
                name__iexact=name.strip(),
            )
            .first()
        )

    # ============================================================
    # ENSURE OPTION
    # ============================================================

    @staticmethod
    @transaction.atomic
    def ensure_option(
        product: Product,
        name: str,
        *,
        slug: str | None = None,
        sort_order: int = 0,
        is_active: bool = True,
    ) -> ProductOption:
        """
        Get an existing option or create it.

        Note:
            Database uniqueness is based on exact name/slug
            values. Application-level case-insensitive matching
            is used before creation.
        """

        normalized_name = name.strip()

        existing = (
            ProductOption.objects
            .filter(
                product_id=product.id,
                name__iexact=normalized_name,
            )
            .first()
        )

        if existing:
            return existing

        option_slug = (
            slugify(slug)
            if slug
            else slugify(normalized_name)
        )

        return ProductOption.objects.create(
            product_id=product.id,
            name=normalized_name,
            slug=option_slug,
            sort_order=sort_order,
            is_active=is_active,
        )

    # ============================================================
    # ENSURE OPTION VALUE
    # ============================================================

    @staticmethod
    @transaction.atomic
    def ensure_option_value(
        product_option: ProductOption,
        name: str,
        *,
        slug: str | None = None,
        sort_order: int = 0,
        is_active: bool = True,
    ) -> ProductOptionValue:
        """
        Get an existing option value or create it.
        """

        normalized_name = name.strip()

        existing = (
            ProductOptionValue.objects
            .filter(
                option_id=product_option.id,
                name__iexact=normalized_name,
            )
            .first()
        )

        if existing:
            return existing

        value_slug = (
            slugify(slug)
            if slug
            else slugify(normalized_name)
        )

        return ProductOptionValue.objects.create(
            option_id=product_option.id,
            name=normalized_name,
            slug=value_slug,
            sort_order=sort_order,
            is_active=is_active,
        )

    # ============================================================
    # VALIDATION
    # ============================================================

    @staticmethod
    def validate_product_options(product: Product) -> dict:
        """
        Validate the product's option/variant configuration.

        Product type is determined by whether variants exist.
        """

        option_count = product.options.count()
        variants_count = product.variants.count()

        messages = []

        is_variable = variants_count > 0

        # --------------------------------------------------------
        # Variable product
        # --------------------------------------------------------

        if is_variable:

            if option_count == 0:
                messages.append(
                    "Variable product has no options defined."
                )

            active_options = (
                product.options
                .filter(
                    is_active=True,
                )
                .prefetch_related(
                    "values",
                )
            )

            for option in active_options:

                # Use prefetched values rather than
                # option.has_values, because has_values
                # performs .exists().
                values = getattr(
                    option,
                    "_prefetched_objects_cache",
                    {},
                ).get(
                    "values",
                    [],
                )

                if not values:
                    messages.append(
                        f"Option '{option.name}' has "
                        "no values defined."
                    )

        # --------------------------------------------------------
        # Simple product
        # --------------------------------------------------------

        else:

            if option_count > 0:
                messages.append(
                    "Simple product has options defined. "
                    "Options are normally used for variable products."
                )

        return {
            "is_valid": not messages,
            "product_type": (
                "variable"
                if is_variable
                else "simple"
            ),
            "option_count": option_count,
            "variants_count": variants_count,
            "messages": messages,
        }