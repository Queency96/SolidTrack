"""
Seed demo vendor, store, category, product and variant data.

Creates:

- Product categories.
- Vendor users and their VendorProfile records.
- Stores per vendor.
- Products per store.
- Variants per product.

The command is idempotent:
re-running it fills in missing records and updates the
seeded records without creating duplicates.

Example:

    python manage.py seed_vendors

Custom amounts:

    python manage.py seed_vendors --vendors 5 --stores 3 --products 30

Custom password:

    python manage.py seed_vendors --password DemoPass123!
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import User
from vendors.models import (
    Product,
    ProductCategory,
    ProductVariant,
    VendorProfile,
    VendorStore,
)


# ============================================================================
# DEFAULT SETTINGS
# ============================================================================

DEFAULT_PASSWORD = "DemoPass123!"


# ============================================================================
# CATEGORIES
# ============================================================================

CATEGORIES = [
    ("Electronics", "electronics"),
    ("Clothing", "clothing"),
    ("Home & Garden", "home-and-garden"),
    ("Sports", "sports"),
    ("Toys", "toys"),
]


# ============================================================================
# VENDORS
# ============================================================================

VENDOR_SCHEMAS = [
    {
        "email": "vendor1@seed.com",
        "first_name": "Ada",
        "last_name": "Okafor",
        "company_name": "SwiftMart Lagos",
    },
    {
        "email": "vendor2@seed.com",
        "first_name": "Emeka",
        "last_name": "Nwosu",
        "company_name": "FreshPick Abuja",
    },
    {
        "email": "vendor3@seed.com",
        "first_name": "Tolu",
        "last_name": "Adebayo",
        "company_name": "DailyNeeds Port Harcourt",
    },
    {
        "email": "vendor4@seed.com",
        "first_name": "Chidi",
        "last_name": "Eze",
        "company_name": "CornerShop Ibadan",
    },
    {
        "email": "vendor5@seed.com",
        "first_name": "Ngozi",
        "last_name": "Bello",
        "company_name": "SaharaMart Kano",
    },
]


# ============================================================================
# STORES
# ============================================================================

STORES = [
    {
        "name": "Main Store",
        "address_line_1": "12 Market Road",
        "city": "Lagos",
        "state": "Lagos",
        "latitude": Decimal("6.524400"),
        "longitude": Decimal("3.379200"),
    },
    {
        "name": "City Store",
        "address_line_1": "25 Commerce Street",
        "city": "Lagos",
        "state": "Lagos",
        "latitude": Decimal("6.601800"),
        "longitude": Decimal("3.351500"),
    },
    {
        "name": "Express Store",
        "address_line_1": "8 Shopping Avenue",
        "city": "Lagos",
        "state": "Lagos",
        "latitude": Decimal("6.465400"),
        "longitude": Decimal("3.406400"),
    },
]


# ============================================================================
# VARIANTS
# ============================================================================

VARIANT_STYLES = [
    {
        "name": "Standard",
        "price_offset": Decimal("0.00"),
        "is_default": True,
    },
    {
        "name": "Premium",
        "price_offset": Decimal("1500.00"),
        "is_default": False,
    },
]


# ============================================================================
# COMMAND
# ============================================================================


class Command(BaseCommand):
    help = (
        "Seed demo vendors, stores, categories, products and variants. "
        "The command is idempotent."
    )

    # ------------------------------------------------------------------
    # Command arguments
    # ------------------------------------------------------------------

    def add_arguments(self, parser):
        parser.add_argument(
            "--vendors",
            type=int,
            default=5,
            help="Number of vendors to create. Maximum: 5.",
        )

        parser.add_argument(
            "--stores",
            type=int,
            default=3,
            help="Number of stores per vendor. Maximum: 3.",
        )

        parser.add_argument(
            "--products",
            type=int,
            default=30,
            help="Number of products per store.",
        )

        parser.add_argument(
            "--password",
            type=str,
            default=DEFAULT_PASSWORD,
            help="Password assigned to newly created demo vendor users.",
        )

    # ------------------------------------------------------------------
    # Main command
    # ------------------------------------------------------------------

    @transaction.atomic
    def handle(self, *args, **options):

        vendor_limit = options["vendors"]
        store_limit = options["stores"]
        products_per_store = options["products"]
        default_password = options["password"]

        # --------------------------------------------------------------
        # Validate arguments
        # --------------------------------------------------------------

        if vendor_limit < 1:
            self.stdout.write(
                self.style.ERROR(
                    "--vendors must be at least 1."
                )
            )
            return

        if vendor_limit > len(VENDOR_SCHEMAS):
            self.stdout.write(
                self.style.ERROR(
                    f"--vendors cannot exceed {len(VENDOR_SCHEMAS)}."
                )
            )
            return

        if store_limit < 1:
            self.stdout.write(
                self.style.ERROR(
                    "--stores must be at least 1."
                )
            )
            return

        if store_limit > len(STORES):
            self.stdout.write(
                self.style.ERROR(
                    f"--stores cannot exceed {len(STORES)}."
                )
            )
            return

        if products_per_store < 1:
            self.stdout.write(
                self.style.ERROR(
                    "--products must be at least 1."
                )
            )
            return

        # --------------------------------------------------------------
        # Header
        # --------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Starting demo marketplace seed..."
            )
        )
        self.stdout.write("")

        # --------------------------------------------------------------
        # 1. Categories
        # --------------------------------------------------------------

        categories = []

        for category_name, category_slug in CATEGORIES:

            category, _ = ProductCategory.objects.get_or_create(
                slug=category_slug,
                defaults={
                    "name": category_name,
                },
            )

            # Keep seeded category names synchronized.
            if category.name != category_name:
                category.name = category_name
                category.save(update_fields=["name"])

            categories.append(category)

        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ {len(categories)} categories ensured"
            )
        )

        # --------------------------------------------------------------
        # 2. Vendors
        # --------------------------------------------------------------

        vendors = []

        for index, schema in enumerate(
            VENDOR_SCHEMAS[:vendor_limit],
            start=1,
        ):
            phone_number = f"0805{index}0000{index}01"

            user, user_created = User.objects.get_or_create(
                email=schema["email"],
                defaults={
                    "first_name": schema["first_name"],
                    "last_name": schema["last_name"],
                    "phone_number": phone_number,
                    "role": User.Roles.VENDOR,
                    "is_active": True,
                    "is_email_verified": True,
                    "is_phone_verified": True,
                },
            )

            # ----------------------------------------------------------
            # Synchronize existing user
            # ----------------------------------------------------------

            user_changed_fields = []

            if user.first_name != schema["first_name"]:
                user.first_name = schema["first_name"]
                user_changed_fields.append("first_name")

            if user.last_name != schema["last_name"]:
                user.last_name = schema["last_name"]
                user_changed_fields.append("last_name")

            if user.phone_number != phone_number:
                user.phone_number = phone_number
                user_changed_fields.append("phone_number")

            if user.role != User.Roles.VENDOR:
                user.role = User.Roles.VENDOR
                user_changed_fields.append("role")

            if not user.is_active:
                user.is_active = True
                user_changed_fields.append("is_active")

            if not user.is_email_verified:
                user.is_email_verified = True
                user_changed_fields.append("is_email_verified")

            if not user.is_phone_verified:
                user.is_phone_verified = True
                user_changed_fields.append("is_phone_verified")

            if user_changed_fields:
                user.save(update_fields=user_changed_fields)

            # ----------------------------------------------------------
            # Password
            # ----------------------------------------------------------

            if user_created or not user.has_usable_password():
                user.set_password(default_password)
                user.save(update_fields=["password"])

            # ----------------------------------------------------------
            # Vendor profile
            # ----------------------------------------------------------

            profile, profile_created = VendorProfile.objects.get_or_create(
                user=user,
                defaults={
                    "company_name": schema["company_name"],
                    "verification_status": (
                        VendorProfile.VerificationStatus.APPROVED
                    ),
                    "approved_at": timezone.now(),
                },
            )

            profile_changed_fields = []

            if profile.company_name != schema["company_name"]:
                profile.company_name = schema["company_name"]
                profile_changed_fields.append("company_name")

            if (
                profile.verification_status
                != VendorProfile.VerificationStatus.APPROVED
            ):
                profile.verification_status = (
                    VendorProfile.VerificationStatus.APPROVED
                )
                profile.approved_at = timezone.now()
                profile_changed_fields.extend(
                    [
                        "verification_status",
                        "approved_at",
                    ]
                )

            elif profile.approved_at is None:
                profile.approved_at = timezone.now()
                profile_changed_fields.append("approved_at")

            if profile_changed_fields:
                profile.save(
                    update_fields=profile_changed_fields
                )

            vendors.append(
                (
                    index,
                    profile,
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ {len(vendors)} vendors ensured"
            )
        )

        # --------------------------------------------------------------
        # 3. Stores + Products + Variants
        # --------------------------------------------------------------

        store_count = 0
        product_count = 0
        variant_count = 0

        for vendor_number, profile in vendors:

            for store_index, spec in enumerate(
                STORES[:store_limit],
                start=1,
            ):

                store_slug = slugify(
                    f"store-{vendor_number}-{store_index}"
                )

                store, _ = VendorStore.objects.get_or_create(
                    vendor=profile,
                    slug=store_slug,
                    defaults={
                        "name": spec["name"],
                        "address_line_1": spec["address_line_1"],
                        "city": spec["city"],
                        "state": spec["state"],
                        "latitude": spec["latitude"],
                        "longitude": spec["longitude"],
                        "is_active": True,
                        "is_verified": True,
                        "accepting_orders": True,
                        "accepting_pickups": True,
                        "is_default": store_index == 1,
                        "preparation_time_minutes": 15,
                    },
                )

                # ------------------------------------------------------
                # Synchronize store data
                # ------------------------------------------------------

                store_changed_fields = []

                store_values = {
                    "name": spec["name"],
                    "address_line_1": spec["address_line_1"],
                    "city": spec["city"],
                    "state": spec["state"],
                    "latitude": spec["latitude"],
                    "longitude": spec["longitude"],
                    "is_active": True,
                    "is_verified": True,
                    "accepting_orders": True,
                    "accepting_pickups": True,
                    "preparation_time_minutes": 15,
                }

                for field_name, value in store_values.items():
                    if getattr(store, field_name) != value:
                        setattr(store, field_name, value)
                        store_changed_fields.append(field_name)

                desired_default = store_index == 1

                if store.is_default != desired_default:
                    store.is_default = desired_default
                    store_changed_fields.append("is_default")

                if store_changed_fields:
                    store.save(
                        update_fields=store_changed_fields
                    )

                # ------------------------------------------------------
                # Ensure only one default store for this vendor
                # ------------------------------------------------------

                if store_index == 1:
                    VendorStore.objects.filter(
                        vendor=profile,
                        is_default=True,
                    ).exclude(
                        pk=store.pk
                    ).update(
                        is_default=False
                    )

                store_count += 1

                # ------------------------------------------------------
                # Products
                # ------------------------------------------------------

                for product_index in range(
                    1,
                    products_per_store + 1,
                ):

                    category = categories[
                        (product_index - 1) % len(categories)
                    ]

                    product_name = (
                        f"Product {product_index} - "
                        f"{store.name}"
                    )

                    product_slug = slugify(
                        f"product-{vendor_number}-"
                        f"{store_index}-"
                        f"{product_index}"
                    )

                    sku = (
                        f"SKU-"
                        f"{vendor_number:02d}"
                        f"{store_index:02d}"
                        f"{product_index:03d}"
                    )

                    price = Decimal(
                        str(
                            500
                            + (product_index % 20) * 250
                            + ((product_index * 13) % 10)
                        )
                    )

                    compare_at_price = None

                    if product_index % 5 == 0:
                        compare_at_price = (
                            price + Decimal("1000.00")
                        )

                    stock_quantity = (
                        (product_index * 17) % 95
                    ) + 5

                    short_description = (
                        f"{category.name} essential "
                        f"from {store.name}."
                    )

                    description = (
                        f"A quality "
                        f"{category.name.lower()} product "
                        f"supplied by "
                        f"{profile.company_name} "
                        f"via {store.name}."
                    )

                    product, _ = Product.objects.get_or_create(
                        vendor=profile,
                        slug=product_slug,
                        defaults={
                            "store": store,
                            "category": category,
                            "name": product_name,
                            "sku": sku,
                            "short_description": short_description,
                            "description": description,
                            "price": price,
                            "compare_at_price": compare_at_price,
                            "stock_quantity": stock_quantity,
                            "track_inventory": True,
                            "is_active": True,
                            "is_published": True,
                            "is_featured": product_index % 10 == 3,
                            "sort_order": product_index,
                        },
                    )

                    # --------------------------------------------------
                    # Synchronize existing product
                    # --------------------------------------------------

                    product_changed_fields = []

                    product_values = {
                        "store": store,
                        "category": category,
                        "name": product_name,
                        "sku": sku,
                        "short_description": short_description,
                        "description": description,
                        "price": price,
                        "compare_at_price": compare_at_price,
                        "stock_quantity": stock_quantity,
                        "track_inventory": True,
                        "is_active": True,
                        "is_published": True,
                        "is_featured": product_index % 10 == 3,
                        "sort_order": product_index,
                    }

                    for field_name, value in product_values.items():

                        if getattr(product, field_name) != value:
                            setattr(
                                product,
                                field_name,
                                value,
                            )
                            product_changed_fields.append(
                                field_name
                            )

                    if product_changed_fields:
                        product.save(
                            update_fields=product_changed_fields
                        )

                    product_count += 1

                    # --------------------------------------------------
                    # Product Variants
                    # --------------------------------------------------

                    for variant_index, style in enumerate(
                        VARIANT_STYLES,
                        start=1,
                    ):

                        variant_sku = (
                            f"{product.sku}-"
                            f"{variant_index:02d}"
                        )

                        variant_price = (
                            price
                            + style["price_offset"]
                        )

                        variant, _ = (
                            ProductVariant.objects.get_or_create(
                                product=product,
                                name=style["name"],
                                defaults={
                                    "sku": variant_sku,
                                    "price": variant_price,
                                    "stock_quantity": stock_quantity,
                                    "track_inventory": True,
                                    "is_active": True,
                                    "is_default": style[
                                        "is_default"
                                    ],
                                    "is_available": True,
                                    "sort_order": variant_index,
                                },
                            )
                        )

                        # ----------------------------------------------
                        # Synchronize existing variant
                        # ----------------------------------------------

                        variant_changed_fields = []

                        variant_values = {
                            "sku": variant_sku,
                            "price": variant_price,
                            "stock_quantity": stock_quantity,
                            "track_inventory": True,
                            "is_active": True,
                            "is_default": style["is_default"],
                            "is_available": True,
                            "sort_order": variant_index,
                        }

                        for field_name, value in variant_values.items():

                            if getattr(
                                variant,
                                field_name,
                            ) != value:

                                setattr(
                                    variant,
                                    field_name,
                                    value,
                                )

                                variant_changed_fields.append(
                                    field_name
                                )

                        if variant_changed_fields:
                            variant.save(
                                update_fields=(
                                    variant_changed_fields
                                )
                            )

                        variant_count += 1

        # --------------------------------------------------------------
        # 4. Ensure exactly one default variant per product
        # --------------------------------------------------------------

        for product in Product.objects.filter(
            vendor__in=[
                profile for _, profile in vendors
            ]
        ):
            default_variants = ProductVariant.objects.filter(
                product=product,
                is_default=True,
            ).order_by("sort_order", "pk")

            first_default = default_variants.first()

            if first_default:
                default_variants.exclude(
                    pk=first_default.pk
                ).update(
                    is_default=False
                )

            else:
                first_variant = (
                    ProductVariant.objects.filter(
                        product=product
                    )
                    .order_by("sort_order", "pk")
                    .first()
                )

                if first_variant:
                    first_variant.is_default = True
                    first_variant.save(
                        update_fields=["is_default"]
                    )

        # --------------------------------------------------------------
        # Summary
        # --------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "✓ Stores, products and variants ensured"
            )
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Seed Summary"
            )
        )

        self.stdout.write(
            f"  Vendors:   {len(vendors)}"
        )

        self.stdout.write(
            f"  Stores:    {store_count}"
        )

        self.stdout.write(
            f"  Products:  {product_count}"
        )

        self.stdout.write(
            f"  Variants:  {variant_count}"
        )

        self.stdout.write(
            f"  Categories: {len(categories)}"
        )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data seeding completed successfully."
            )
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                f"Demo vendor password: {default_password}"
            )
        )