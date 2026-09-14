"""
Signals for the vendors app.
"""
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify

from vendors.models import (
    Product,
    ProductOption,
    CategoryOption,
)


@receiver(post_save, sender=Product)
def create_product_options_from_category(sender, instance, created, **kwargs):
    """
    Auto-create ProductOption records from CategoryOption templates
    when a product is created or its category changes.
    
    This ensures products have the appropriate options defined
    based on their category.
    """
    
    # Only process if this is a new product or category was updated
    if not created:
        # For updates, we'll check if category changed in the view layer
        # to avoid unnecessary processing on every save
        return
    
    # Get category options for the product's category
    category = instance.category
    if not category:
        return
    
    # Get all category options (including inherited ones)
    category_options = CategoryOption.objects.filter(
        category=category,
        is_active=True,
    ).select_related('category')
    
    # Create ProductOption records
    with transaction.atomic():
        for cat_option in category_options:
            # Check if option already exists
            option_exists = ProductOption.objects.filter(
                product=instance,
                name__iexact=cat_option.name,
            ).exists()
            
            if not option_exists:
                ProductOption.objects.create(
                    product=instance,
                    name=cat_option.name,
                    slug=slugify(cat_option.name),
                    sort_order=cat_option.sort_order,
                    is_active=True,
                )
