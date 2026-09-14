from django.core.management.base import BaseCommand, CommandError

from vendors.models import Product
from vendors.services.product_option_service import ProductOptionService


class Command(BaseCommand):
    """Management command to backfill product options from category options."""

    help = (
        "Backfill ProductOption records for existing products "
        "based on their category's CategoryOption templates."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Show what would be created without making changes.",
        )
        parser.add_argument(
            "--vendor-id",
            type=str,
            dest="vendor_id",
            help="Only process products for a specific vendor (by UUID).",
        )
        parser.add_argument(
            "--product-id",
            type=str,
            dest="product_id",
            help="Only process a specific product (by UUID).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            default=False,
            help="Overwrite existing options if they already exist.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        vendor_id = options.get("vendor_id")
        product_id = options.get("product_id")
        force = options.get("force", False)

        # Build queryset
        queryset = Product.objects.all()

        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
            self.stdout.write(f"Filtering by vendor: {vendor_id}")

        if product_id:
            queryset = queryset.filter(id=product_id)
            self.stdout.write(f"Filtering by product: {product_id}")

        total_products = queryset.count()

        if total_products == 0:
            self.stdout.write(
                self.style.WARNING("No products found to process.")
            )
            return

        self.stdout.write(
            f"Found {total_products} product(s) to process."
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made.")
            )

        total_options_created = 0
        total_products_processed = 0

        for product in queryset:
            product_name = product.name
            category_name = (
                product.category.name if product.category else "No Category"
            )

            # Get current options count
            existing_options_count = product.options.count()

            # Get applicable category options
            category_options = ProductOptionService.get_category_options_for_product(
                product
            )
            applicable_count = category_options.count()

            if not force and existing_options_count > 0:
                self.stdout.write(
                    f"  - {product_name} ({category_name}): "
                    f"SKIPPED (has {existing_options_count} existing options, "
                    "use --force to overwrite)"
                )
                continue

            if dry_run:
                # Show what would be created
                self.stdout.write(
                    f"  - {product_name} ({category_name}): "
                    f"Would create {applicable_count} options"
                )
                total_options_created += applicable_count
            else:
                # Actually create the options
                created_count = ProductOptionService.create_options_from_category(
                    product
                )
                total_options_created += created_count
                self.stdout.write(
                    f"  - {product_name} ({category_name}): "
                    f"Created {created_count} options"
                )

            total_products_processed += 1

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(
            f"Summary: Processed {total_products_processed} product(s)"
        )
        self.stdout.write(
            f"Options created: {total_options_created}"
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "This was a dry run. Run without --dry-run to apply changes."
                )
            )