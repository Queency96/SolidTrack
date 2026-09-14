"""
Service layer for product options management.

Handles auto-creation of ProductOption records from CategoryOption templates
and provides utilities for both variable products (with variants) and simple
products (without variants).
"""
from django.db import transaction
from django.utils.text import slugify

from vendors.models import (
    Product,
    ProductOption,
    ProductOptionValue,
    CategoryOption,
)


class ProductOptionService:
    """Service for managing product options."""
    
    @staticmethod
    @transaction.atomic
    def create_options_from_category(product: Product) -> int:
        """
        Auto-create ProductOption records from CategoryOption templates.
        
        This is called when a product is created or its category changes.
        Returns the number of options created.
        
        Args:
            product: The product instance
            
        Returns:
            int: Number of ProductOption records created
        """
        if not product.category:
            return 0
        
        created_count = 0
        category = product.category
        
        # Get all active category options for this category
        category_options = CategoryOption.objects.filter(
            category=category,
            is_active=True,
        ).order_by('sort_order', 'name')
        
        for cat_option in category_options:
            # Avoid duplicates
            option_exists = ProductOption.objects.filter(
                product=product,
                name__iexact=cat_option.name,
            ).exists()
            
            if not option_exists:
                ProductOption.objects.create(
                    product=product,
                    name=cat_option.name,
                    slug=slugify(cat_option.name),
                    sort_order=cat_option.sort_order,
                    is_active=True,
                )
                created_count += 1
        
        return created_count
    
    @staticmethod
    def get_category_options_for_product(product: Product) -> list:
        """
        Get all applicable category options for a product.
        
        Args:
            product: The product instance
            
        Returns:
            list: QuerySet of CategoryOption
        """
        if not product.category:
            return CategoryOption.objects.none()
        
        return CategoryOption.objects.filter(
            category=product.category,
            is_active=True,
        ).order_by('sort_order', 'name')
    
    @staticmethod
    def is_variable_product(product: Product) -> bool:
        """
        Determine if a product is a variable product (has variants).
        
        Args:
            product: The product instance
            
        Returns:
            bool: True if product has variants, False otherwise
        """
        return product.variants.exists()
    
    @staticmethod
    def is_simple_product(product: Product) -> bool:
        """
        Determine if a product is a simple product (no variants).
        
        Args:
            product: The product instance
            
        Returns:
            bool: True if product has no variants, False otherwise
        """
        return not product.variants.exists()
    
    @staticmethod
    def get_product_type(product: Product) -> str:
        """
        Get the product type as a string.
        
        Args:
            product: The product instance
            
        Returns:
            str: Either 'variable' or 'simple'
        """
        return 'variable' if ProductOptionService.is_variable_product(product) else 'simple'
    
    @staticmethod
    def validate_product_options(product: Product) -> dict:
        """
        Validate that a product has all required options properly configured.
        
        Returns validation status and any warnings.
        
        Args:
            product: The product instance
            
        Returns:
            dict: Validation result with keys:
                - is_valid: bool
                - product_type: str ('simple' or 'variable')
                - option_count: int
                - variants_count: int
                - messages: list of validation messages
        """
        messages = []
        option_count = product.options.count()
        variants_count = product.variants.count()
        is_variable = ProductOptionService.is_variable_product(product)
        
        if is_variable:
            # Variable product validations
            if option_count == 0:
                messages.append(
                    "Variable product has no options defined. "
                    "Vendors should define options before creating variants."
                )
            
            if variants_count == 0:
                messages.append(
                    "Variable product has options but no variants. "
                    "At least one variant should be created."
                )
            
            # Check if all options have at least one value
            for option in product.options.filter(is_active=True):
                if not option.has_values:
                    messages.append(
                        f"Option '{option.name}' has no values defined."
                    )
        else:
            # Simple product validations
            if option_count > 0:
                messages.append(
                    "Simple product (no variants) has options defined. "
                    "Options are typically used for variable products."
                )
        
        return {
            'is_valid': len(messages) == 0,
            'product_type': 'variable' if is_variable else 'simple',
            'option_count': option_count,
            'variants_count': variants_count,
            'messages': messages,
        }
