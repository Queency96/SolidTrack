"""
This management command creates initial categories in the ProductCategory model.
"""

from django.core.management.base import BaseCommand
from vendors.models import ProductCategory

class Command(BaseCommand):
    help = "Create product categories"

    def handle(self, *args, **options):
        categories = [
            ("Electronics", "electronics"),
            ("Clothing", "clothing"),
            ("Home & Garden", "home-and-garden"),
            ("Sports", "sports"),
            ("Toys", "toys"),
        ]

        if ProductCategory.objects.exists():
            self.stdout.write(self.style.WARNING('Categories already exist.'))
            return

        for name, slug in categories:
            category, created = ProductCategory.objects.get_or_create(
                name=name,
                slug=slug,
            )
            action = 'Created' if created else 'Exists'
            self.stdout.write(self.style.SUCCESS(f'{action} category: {name}'))
