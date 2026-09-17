import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import time
from decimal import Decimal
from html import escape
from itertools import product as cartesian_product

import cloudinary.uploader

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from vendors.models import (
    CategoryOption,
    Product,
    ProductCategory,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
    ProductVariantImage,
    ProductVariantOptionValue,
    StoreOperatingHour,
    VendorProfile,
)


class Command(BaseCommand):
    help = (
        "Create mock products, categories, options, variants, variant "
        "option values, Cloudinary images, and store operating hours."
    )

    # =========================================================
    # IMAGE GENERATION CONFIGURATION
    # =========================================================

    # Number of gallery images generated for every variant.
    IMAGES_PER_VARIANT = 3

    # Number of simultaneous Cloudinary uploads.
    CLOUDINARY_WORKERS = 8

    # Cloudinary root folder.
    CLOUDINARY_FOLDER = "mock-products"

    # Whether deterministic Cloudinary public IDs should be overwritten.
    CLOUDINARY_OVERWRITE = True

    # =========================================================
    # GENERAL CONFIGURATION
    # =========================================================

    DEFAULT_PRODUCTS_PER_STORE = 30
    DEFAULT_VARIANT_PRODUCTS = 20
    DEFAULT_NON_VARIANT_PRODUCTS = 10

    VARIANTS_PER_PRODUCT = 6

    MOCK_VENDOR_DOMAIN = "@soliddistributor.com"

    RANDOM_SEED = 20260915

    # =========================================================
    # PRODUCT DEFINITIONS
    # =========================================================

    VARIANT_PRODUCTS = [
        {
            "name": "Apple iPhone 15",
            "category": "Smartphones",
            "price": Decimal("850000"),
            "short_description": (
                "Premium Apple smartphone with advanced camera system."
            ),
            "description": (
                "Apple iPhone 15 with a modern design, powerful performance, "
                "excellent cameras and all-day battery life."
            ),
        },
        {
            "name": "Samsung Galaxy S24",
            "category": "Smartphones",
            "price": Decimal("920000"),
            "short_description": (
                "Flagship Samsung smartphone with premium performance."
            ),
            "description": (
                "Samsung Galaxy S24 featuring a high-resolution display, "
                "powerful processor and advanced camera capabilities."
            ),
        },
        {
            "name": "Google Pixel 9",
            "category": "Smartphones",
            "price": Decimal("880000"),
            "short_description": (
                "Google smartphone with intelligent camera features."
            ),
            "description": (
                "Google Pixel 9 delivers clean Android software, "
                "excellent photography and smooth everyday performance."
            ),
        },
        {
            "name": "Apple MacBook Air",
            "category": "Laptops",
            "price": Decimal("1450000"),
            "short_description": (
                "Slim and powerful Apple laptop for work and study."
            ),
            "description": (
                "Apple MacBook Air designed for productivity, portability "
                "and everyday professional computing."
            ),
        },
        {
            "name": "Dell XPS 15",
            "category": "Laptops",
            "price": Decimal("1650000"),
            "short_description": (
                "Premium Dell laptop for demanding workloads."
            ),
            "description": (
                "Dell XPS 15 combines premium construction, strong performance "
                "and a high-quality display."
            ),
        },
        {
            "name": "HP Spectre x360",
            "category": "Laptops",
            "price": Decimal("1550000"),
            "short_description": (
                "Convertible premium HP laptop."
            ),
            "description": (
                "HP Spectre x360 is a versatile convertible laptop "
                "for productivity, creativity and entertainment."
            ),
        },
        {
            "name": "Lenovo ThinkPad X1 Carbon",
            "category": "Laptops",
            "price": Decimal("1750000"),
            "short_description": (
                "Business-focused Lenovo laptop."
            ),
            "description": (
                "Lenovo ThinkPad X1 Carbon provides business-class "
                "performance, portability and durability."
            ),
        },
        {
            "name": "Samsung 55-inch Smart TV",
            "category": "Televisions",
            "price": Decimal("780000"),
            "short_description": (
                "55-inch Samsung smart television."
            ),
            "description": (
                "Samsung Smart TV with a large high-quality display, "
                "smart streaming features and immersive entertainment."
            ),
        },
        {
            "name": "LG 55-inch OLED TV",
            "category": "Televisions",
            "price": Decimal("1100000"),
            "short_description": (
                "Premium LG OLED television."
            ),
            "description": (
                "LG OLED TV delivers deep blacks, vibrant colours "
                "and an immersive home entertainment experience."
            ),
        },
        {
            "name": "Sony Bravia 55-inch TV",
            "category": "Televisions",
            "price": Decimal("980000"),
            "short_description": (
                "Sony Bravia smart television."
            ),
            "description": (
                "Sony Bravia television with excellent picture quality, "
                "smart features and premium sound support."
            ),
        },
        {
            "name": "Apple AirPods Pro",
            "category": "Audio",
            "price": Decimal("390000"),
            "short_description": (
                "Premium wireless earbuds with noise cancellation."
            ),
            "description": (
                "Apple AirPods Pro provide immersive sound, active noise "
                "cancellation and a compact wireless design."
            ),
        },
        {
            "name": "Sony WH-1000XM5",
            "category": "Audio",
            "price": Decimal("520000"),
            "short_description": (
                "Premium wireless noise-cancelling headphones."
            ),
            "description": (
                "Sony WH-1000XM5 headphones provide high-quality sound "
                "and advanced active noise cancellation."
            ),
        },
        {
            "name": "JBL Charge 5",
            "category": "Audio",
            "price": Decimal("210000"),
            "short_description": (
                "Portable JBL Bluetooth speaker."
            ),
            "description": (
                "JBL Charge 5 delivers powerful portable audio "
                "with long battery life."
            ),
        },
        {
            "name": "Apple Watch Series 10",
            "category": "Wearables",
            "price": Decimal("520000"),
            "short_description": (
                "Modern Apple smartwatch."
            ),
            "description": (
                "Apple Watch Series 10 combines health, fitness, "
                "communication and smart features."
            ),
        },
        {
            "name": "Samsung Galaxy Watch 7",
            "category": "Wearables",
            "price": Decimal("390000"),
            "short_description": (
                "Samsung smartwatch with health tracking."
            ),
            "description": (
                "Galaxy Watch 7 provides fitness tracking, notifications, "
                "health monitoring and smart functionality."
            ),
        },
        {
            "name": "Nike Air Max",
            "category": "Shoes",
            "price": Decimal("180000"),
            "short_description": (
                "Comfortable Nike lifestyle sneakers."
            ),
            "description": (
                "Nike Air Max sneakers designed for everyday comfort, "
                "style and casual activities."
            ),
        },
        {
            "name": "Adidas Ultraboost",
            "category": "Shoes",
            "price": Decimal("210000"),
            "short_description": (
                "Performance running shoes from Adidas."
            ),
            "description": (
                "Adidas Ultraboost running shoes designed for responsive "
                "cushioning and everyday running."
            ),
        },
        {
            "name": "PlayStation 5 Slim",
            "category": "Gaming",
            "price": Decimal("850000"),
            "short_description": (
                "Sony PlayStation 5 Slim gaming console."
            ),
            "description": (
                "PlayStation 5 Slim delivers next-generation gaming "
                "performance with a compact console design."
            ),
        },
        {
            "name": "Xbox Series X",
            "category": "Gaming",
            "price": Decimal("780000"),
            "short_description": (
                "Microsoft Xbox Series X console."
            ),
            "description": (
                "Xbox Series X provides high-performance gaming, "
                "fast loading and 4K gaming capabilities."
            ),
        },
        {
            "name": "Nintendo Switch OLED",
            "category": "Gaming",
            "price": Decimal("480000"),
            "short_description": (
                "Nintendo hybrid gaming console."
            ),
            "description": (
                "Nintendo Switch OLED supports handheld, tabletop "
                "and television gaming."
            ),
        },
    ]

    NON_VARIANT_PRODUCTS = [
        {
            "name": "USB-C Fast Charging Cable",
            "category": "Accessories",
            "price": Decimal("15000"),
            "short_description": (
                "Durable USB-C fast charging cable."
            ),
            "description": (
                "High-quality USB-C cable suitable for charging "
                "and data transfer."
            ),
        },
        {
            "name": "65W USB-C Charger",
            "category": "Accessories",
            "price": Decimal("35000"),
            "short_description": (
                "Compact 65W USB-C power adapter."
            ),
            "description": (
                "Fast USB-C charger suitable for phones, tablets "
                "and compatible laptops."
            ),
        },
        {
            "name": "Wireless Mouse",
            "category": "Computer Accessories",
            "price": Decimal("22000"),
            "short_description": (
                "Comfortable wireless computer mouse."
            ),
            "description": (
                "Reliable wireless mouse for office, school "
                "and home computing."
            ),
        },
        {
            "name": "Laptop Backpack",
            "category": "Bags",
            "price": Decimal("45000"),
            "short_description": (
                "Protective laptop backpack."
            ),
            "description": (
                "Spacious laptop backpack with multiple compartments."
            ),
        },
        {
            "name": "Power Bank 20000mAh",
            "category": "Accessories",
            "price": Decimal("50000"),
            "short_description": (
                "High-capacity portable power bank."
            ),
            "description": (
                "20,000mAh portable battery for charging compatible "
                "devices on the go."
            ),
        },
        {
            "name": "Tempered Glass Screen Protector",
            "category": "Accessories",
            "price": Decimal("10000"),
            "short_description": (
                "Protective tempered glass screen protector."
            ),
            "description": (
                "Durable tempered glass designed to protect "
                "smartphone displays."
            ),
        },
        {
            "name": "Bluetooth USB Adapter",
            "category": "Computer Accessories",
            "price": Decimal("12000"),
            "short_description": (
                "Compact Bluetooth adapter for computers."
            ),
            "description": (
                "USB Bluetooth adapter for connecting compatible "
                "wireless devices."
            ),
        },
        {
            "name": "HDMI Cable",
            "category": "Computer Accessories",
            "price": Decimal("10000"),
            "short_description": (
                "High-speed HDMI cable."
            ),
            "description": (
                "HDMI cable suitable for televisions, monitors, "
                "consoles and computers."
            ),
        },
        {
            "name": "Laptop Stand",
            "category": "Computer Accessories",
            "price": Decimal("30000"),
            "short_description": (
                "Adjustable ergonomic laptop stand."
            ),
            "description": (
                "Adjustable stand designed to improve laptop viewing "
                "height and ergonomics."
            ),
        },
        {
            "name": "Smartphone Tripod",
            "category": "Accessories",
            "price": Decimal("28000"),
            "short_description": (
                "Adjustable smartphone tripod."
            ),
            "description": (
                "Compact tripod for photography, video recording "
                "and online meetings."
            ),
        },
    ]

    # =========================================================
    # CATEGORY OPTIONS
    # =========================================================

    CATEGORY_OPTIONS = {
        "Smartphones": {
            "Color": [
                "Black",
                "White",
                "Blue",
            ],
            "Storage": [
                "128GB",
                "256GB",
            ],
        },
        "Laptops": {
            "Color": [
                "Black",
                "Silver",
                "Gray",
            ],
            "Storage": [
                "512GB",
                "1TB",
            ],
        },
        "Televisions": {
            "Color": [
                "Black",
                "Gray",
                "Silver",
            ],
            "Screen Size": [
                "43-inch",
                "55-inch",
            ],
        },
        "Audio": {
            "Color": [
                "Black",
                "White",
                "Blue",
            ],
            "Storage": [
                "Standard",
                "Premium",
            ],
        },
        "Wearables": {
            "Color": [
                "Black",
                "Silver",
                "Gold",
            ],
            "Storage": [
                "32GB",
                "64GB",
            ],
        },
        "Shoes": {
            "Color": [
                "Black",
                "White",
                "Blue",
            ],
            "Size": [
                "40",
                "42",
            ],
        },
        "Gaming": {
            "Color": [
                "Black",
                "White",
                "Gray",
            ],
            "Storage": [
                "512GB",
                "1TB",
            ],
        },
    }

    # =========================================================
    # STORE OPERATING HOURS
    # =========================================================

    STORE_HOURS = {
        0: (time(8, 0), time(18, 0)),
        1: (time(8, 0), time(18, 0)),
        2: (time(8, 0), time(18, 0)),
        3: (time(8, 0), time(18, 0)),
        4: (time(8, 0), time(18, 0)),
        5: (time(9, 0), time(17, 0)),
        6: (None, None),
    }

    # =========================================================
    # GENERATED IMAGE BACKGROUNDS
    # =========================================================

    IMAGE_BACKGROUNDS = [
        "#F4F4F5",
        "#E5E7EB",
        "#DBEAFE",
        "#DCFCE7",
        "#FEF3C7",
        "#FCE7F3",
        "#EDE9FE",
    ]

    # =========================================================
    # COMMAND ARGUMENTS
    # =========================================================

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help=(
                "Delete existing MOCK products and their Cloudinary "
                "images before creating them."
            ),
        )

        parser.add_argument(
            "--all-vendors",
            action="store_true",
            help=(
                "Create products for every VendorProfile instead of only "
                "mock vendors using the @soliddistributor.com domain."
            ),
        )

        parser.add_argument(
            "--stores-per-vendor",
            type=int,
            default=None,
            help=(
                "Limit the number of stores processed per vendor. "
                "Default: all available stores."
            ),
        )

    # =========================================================
    # HANDLE
    # =========================================================

    def handle(self, *args, **options):
        self.random = random.Random(self.RANDOM_SEED)

        overwrite = options["overwrite"]
        all_vendors = options["all_vendors"]
        stores_per_vendor = options["stores_per_vendor"]

        if stores_per_vendor is not None and stores_per_vendor <= 0:
            raise ValueError(
                "--stores-per-vendor must be greater than zero."
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Starting mock product generation..."
            )
        )
        self.stdout.write("")

        self.validate_configuration()

        # -----------------------------------------------------
        # OVERWRITE
        # -----------------------------------------------------

        if overwrite:
            self.delete_mock_products()

        # -----------------------------------------------------
        # CATEGORIES
        # -----------------------------------------------------

        categories = self.create_categories()

        # -----------------------------------------------------
        # VENDORS
        # -----------------------------------------------------

        vendors = self.get_vendors(
            all_vendors=all_vendors
        )

        if not vendors.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No vendors found."
                )
            )
            return

        # -----------------------------------------------------
        # COUNTERS
        # -----------------------------------------------------

        total_products = 0
        total_variants = 0
        total_images = 0
        total_stores = 0

        # -----------------------------------------------------
        # PROCESS VENDORS
        # -----------------------------------------------------

        for vendor in vendors:
            stores = (
                vendor.stores
                .all()
                .order_by("created_at")
            )

            if stores_per_vendor is not None:
                stores = stores[:stores_per_vendor]

            vendor_store_count = stores.count()

            if vendor_store_count == 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping vendor '{vendor.company_name}': "
                        "no stores found."
                    )
                )
                continue

            self.stdout.write("")
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"Vendor: {vendor.company_name}"
                )
            )

            for store in stores:
                (
                    products_created,
                    variants_created,
                    images_created,
                ) = self.create_products_for_store(
                    vendor=vendor,
                    store=store,
                    categories=categories,
                )

                self.create_store_operating_hours(store)

                total_products += products_created
                total_variants += variants_created
                total_images += images_created
                total_stores += 1

        # -----------------------------------------------------
        # SUMMARY
        # -----------------------------------------------------

        self.stdout.write("")
        self.stdout.write("=" * 70)

        self.stdout.write(
            self.style.SUCCESS(
                "MOCK PRODUCT GENERATION COMPLETED"
            )
        )

        self.stdout.write("=" * 70)

        self.stdout.write(
            f"Stores processed:       {total_stores}"
        )

        self.stdout.write(
            f"Products created:       {total_products}"
        )

        self.stdout.write(
            f"Variants created:       {total_variants}"
        )

        self.stdout.write(
            f"Variant images created: {total_images}"
        )

        self.stdout.write("=" * 70)
        self.stdout.write("")

    # =========================================================
    # VALIDATE CONFIGURATION
    # =========================================================

    def validate_configuration(self):
        if len(self.VARIANT_PRODUCTS) != self.DEFAULT_VARIANT_PRODUCTS:
            raise ValueError(
                f"Expected {self.DEFAULT_VARIANT_PRODUCTS} variant "
                f"product definitions, found "
                f"{len(self.VARIANT_PRODUCTS)}."
            )

        if len(self.NON_VARIANT_PRODUCTS) != (
            self.DEFAULT_NON_VARIANT_PRODUCTS
        ):
            raise ValueError(
                f"Expected {self.DEFAULT_NON_VARIANT_PRODUCTS} "
                f"non-variant product definitions, found "
                f"{len(self.NON_VARIANT_PRODUCTS)}."
            )

        if self.IMAGES_PER_VARIANT <= 0:
            raise ValueError(
                "IMAGES_PER_VARIANT must be greater than zero."
            )

        if self.VARIANTS_PER_PRODUCT <= 0:
            raise ValueError(
                "VARIANTS_PER_PRODUCT must be greater than zero."
            )

        if self.CLOUDINARY_WORKERS <= 0:
            raise ValueError(
                "CLOUDINARY_WORKERS must be greater than zero."
            )

        if self.VARIANTS_PER_PRODUCT > 6:
            raise ValueError(
                "This command currently defines only six price "
                "adjustments. Increase the price adjustment list "
                "before increasing VARIANTS_PER_PRODUCT."
            )

    # =========================================================
    # VENDORS
    # =========================================================

    def get_vendors(self, all_vendors=False):
        queryset = (
            VendorProfile.objects
            .select_related("user")
            .prefetch_related("stores")
            .order_by("created_at")
        )

        if not all_vendors:
            queryset = queryset.filter(
                user__email__iendswith=self.MOCK_VENDOR_DOMAIN
            )

        return queryset

    # =========================================================
    # DELETE MOCK PRODUCTS
    # =========================================================

    def delete_mock_products(self):
        """
        Delete existing mock products and remove their Cloudinary
        assets first.

        This prevents the database from being cleaned while leaving
        hundreds or thousands of orphaned Cloudinary assets.
        """

        self.stdout.write(
            self.style.WARNING(
                "Deleting existing mock products and their images..."
            )
        )

        products = Product.objects.filter(
            sku__startswith="MOCK-"
        ).prefetch_related(
            "variants__images"
        )

        image_public_ids = []

        # -----------------------------------------------------
        # COLLECT CLOUDINARY ASSETS
        # -----------------------------------------------------

        for product in products:
            for variant in product.variants.all():
                for image in variant.images.all():
                    if image.image:
                        public_id = str(image.image)

                        if public_id:
                            image_public_ids.append(
                                public_id
                            )

        # -----------------------------------------------------
        # DELETE CLOUDINARY ASSETS
        # -----------------------------------------------------

        deleted_cloudinary = 0

        for public_id in image_public_ids:
            try:
                result = cloudinary.uploader.destroy(
                    public_id,
                    resource_type="image",
                )

                if result.get("result") in (
                    "ok",
                    "not found",
                ):
                    deleted_cloudinary += 1

            except Exception as exc:
                self.stdout.write(
                    self.style.WARNING(
                        "Could not delete Cloudinary asset "
                        f"'{public_id}': {exc}"
                    )
                )

        # -----------------------------------------------------
        # DELETE DATABASE RECORDS
        # -----------------------------------------------------

        deleted_count, _ = products.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} mock-related database "
                "records."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Cloudinary assets processed: "
                f"{deleted_cloudinary}/{len(image_public_ids)}"
            )
        )

    # =========================================================
    # CATEGORIES
    # =========================================================

    def create_categories(self):
        category_names = set()

        for item in self.VARIANT_PRODUCTS:
            category_names.add(
                item["category"]
            )

        for item in self.NON_VARIANT_PRODUCTS:
            category_names.add(
                item["category"]
            )

        categories = {}

        for sort_order, category_name in enumerate(
            sorted(category_names),
            start=1,
        ):
            category, _ = (
                ProductCategory.objects.get_or_create(
                    slug=slugify(category_name),
                    defaults={
                        "name": category_name,
                        "description": (
                            f"Mock product category for "
                            f"{category_name}."
                        ),
                        "sort_order": sort_order,
                        "is_active": True,
                    },
                )
            )

            updates = []

            if category.name != category_name:
                category.name = category_name
                updates.append("name")

            if category.description != (
                f"Mock product category for {category_name}."
            ):
                category.description = (
                    f"Mock product category for {category_name}."
                )
                updates.append("description")

            if category.sort_order != sort_order:
                category.sort_order = sort_order
                updates.append("sort_order")

            if not category.is_active:
                category.is_active = True
                updates.append("is_active")

            if updates:
                category.save(
                    update_fields=updates
                )

            categories[category_name] = category

            # -------------------------------------------------
            # CATEGORY OPTIONS
            # -------------------------------------------------

            category_options = self.CATEGORY_OPTIONS.get(
                category_name,
                {},
            )

            for option_sort_order, option_name in enumerate(
                category_options.keys(),
                start=1,
            ):
                category_option, _ = (
                    CategoryOption.objects.get_or_create(
                        category=category,
                        slug=slugify(option_name),
                        defaults={
                            "name": option_name,
                            "sort_order": option_sort_order,
                            "is_active": True,
                        },
                    )
                )

                updates = []

                if category_option.name != option_name:
                    category_option.name = option_name
                    updates.append("name")

                if category_option.sort_order != (
                    option_sort_order
                ):
                    category_option.sort_order = (
                        option_sort_order
                    )
                    updates.append("sort_order")

                if not category_option.is_active:
                    category_option.is_active = True
                    updates.append("is_active")

                if updates:
                    category_option.save(
                        update_fields=updates
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Categories ready: {len(categories)}"
            )
        )

        return categories

    # =========================================================
    # CREATE PRODUCTS FOR STORE
    # =========================================================

    def create_products_for_store(
        self,
        vendor,
        store,
        categories,
    ):
        self.stdout.write(
            f"  Store: {store.name}"
        )

        products_created = 0
        variants_created = 0
        images_created = 0

        # =====================================================
        # VARIANT PRODUCTS
        # =====================================================

        for index, definition in enumerate(
            self.VARIANT_PRODUCTS,
            start=1,
        ):
            result = self.create_product(
                vendor=vendor,
                store=store,
                category=categories[
                    definition["category"]
                ],
                definition=definition,
                product_number=index,
                is_variant_product=True,
            )

            if result is None:
                continue

            (
                product_created,
                variant_count,
                image_count,
            ) = result

            if product_created:
                products_created += 1

            variants_created += variant_count
            images_created += image_count

        # =====================================================
        # NON-VARIANT PRODUCTS
        # =====================================================

        non_variant_start = (
            len(self.VARIANT_PRODUCTS) + 1
        )

        for offset, definition in enumerate(
            self.NON_VARIANT_PRODUCTS,
            start=0,
        ):
            result = self.create_product(
                vendor=vendor,
                store=store,
                category=categories[
                    definition["category"]
                ],
                definition=definition,
                product_number=(
                    non_variant_start + offset
                ),
                is_variant_product=False,
            )

            if result is None:
                continue

            (
                product_created,
                variant_count,
                image_count,
            ) = result

            if product_created:
                products_created += 1

            variants_created += variant_count
            images_created += image_count

        self.stdout.write(
            self.style.SUCCESS(
                f"    Products: {products_created} | "
                f"Variants: {variants_created} | "
                f"Images: {images_created}"
            )
        )

        return (
            products_created,
            variants_created,
            images_created,
        )

    # =========================================================
    # CREATE PRODUCT
    # =========================================================

    def create_product(
        self,
        vendor,
        store,
        category,
        definition,
        product_number,
        is_variant_product,
    ):
        product_name = definition["name"]

        product_slug = slugify(
            f"{product_name}-{store.slug}"
        )

        product_sku = (
            f"MOCK-"
            f"{str(vendor.id).replace('-', '')[:8].upper()}-"
            f"{str(store.id).replace('-', '')[:8].upper()}-"
            f"P{product_number:02d}"
        )

        # -----------------------------------------------------
        # IDEMPOTENCY
        # -----------------------------------------------------

        existing_product = (
            Product.objects
            .filter(
                vendor=vendor,
                sku=product_sku,
            )
            .first()
        )

        if existing_product:
            return self.reconcile_existing_product(
                product=existing_product,
                category=category,
                definition=definition,
                is_variant_product=is_variant_product,
            )

        # -----------------------------------------------------
        # PRICE
        # -----------------------------------------------------

        compare_at_price = (
            definition["price"] * Decimal("1.15")
        ).quantize(
            Decimal("0.01")
        )

        # -----------------------------------------------------
        # DATABASE CREATION
        # -----------------------------------------------------

        try:
            with transaction.atomic():
                product = Product.objects.create(
                    vendor=vendor,
                    store=store,
                    category=category,
                    name=product_name,
                    slug=product_slug,
                    sku=product_sku,
                    short_description=(
                        definition["short_description"]
                    ),
                    description=definition["description"],
                    price=definition["price"],
                    compare_at_price=compare_at_price,
                    stock_quantity=self.random.randint(
                        10,
                        100,
                    ),
                    track_inventory=True,
                    is_active=True,
                    is_published=True,
                    is_featured=(
                        product_number <= 5
                    ),
                    sort_order=product_number,
                )

                if is_variant_product:
                    (
                        variant_count,
                        image_count,
                    ) = self.create_product_variants(
                        product=product,
                        category=category,
                        product_number=product_number,
                    )
                else:
                    variant_count = 0
                    image_count = 0

        except Exception:
            raise

        return (
            True,
            variant_count,
            image_count,
        )

    # =========================================================
    # RECONCILE EXISTING PRODUCT
    # =========================================================

    def reconcile_existing_product(
        self,
        product,
        category,
        definition,
        is_variant_product,
    ):
        """
        Repair an existing mock product rather than simply skipping it.

        This makes repeated executions idempotent and allows a partially
        generated product to be completed.
        """

        variant_count = 0
        image_count = 0

        # -----------------------------------------------------
        # UPDATE PRODUCT FIELDS
        # -----------------------------------------------------

        compare_at_price = (
            definition["price"] * Decimal("1.15")
        ).quantize(
            Decimal("0.01")
        )

        updates = []

        desired_values = {
            "category": category,
            "name": definition["name"],
            "short_description": (
                definition["short_description"]
            ),
            "description": definition["description"],
            "price": definition["price"],
            "compare_at_price": compare_at_price,
            "track_inventory": True,
            "is_active": True,
            "is_published": True,
        }

        for field, value in desired_values.items():
            if getattr(product, field) != value:
                setattr(product, field, value)
                updates.append(field)

        if updates:
            product.save(
                update_fields=updates
            )

        # -----------------------------------------------------
        # VARIANT PRODUCT REPAIR
        # -----------------------------------------------------

        if is_variant_product:
            (
                variant_count,
                image_count,
            ) = self.ensure_product_variants(
                product=product,
                category=category,
            )

        return (
            False,
            variant_count,
            image_count,
        )

    # =========================================================
    # CREATE PRODUCT OPTIONS
    # =========================================================

    def create_product_options(
        self,
        product,
        category,
    ):
        category_options = list(
            category.category_options
            .filter(
                is_active=True
            )
            .order_by(
                "sort_order",
                "created_at",
            )
        )

        product_options = []

        for category_option in category_options:
            option, _ = (
                ProductOption.objects.get_or_create(
                    product=product,
                    slug=category_option.slug,
                    defaults={
                        "name": category_option.name,
                        "sort_order": (
                            category_option.sort_order
                        ),
                        "is_active": True,
                    },
                )
            )

            updates = []

            if option.name != category_option.name:
                option.name = category_option.name
                updates.append("name")

            if option.sort_order != (
                category_option.sort_order
            ):
                option.sort_order = (
                    category_option.sort_order
                )
                updates.append("sort_order")

            if not option.is_active:
                option.is_active = True
                updates.append("is_active")

            if updates:
                option.save(
                    update_fields=updates
                )

            product_options.append(option)

            # -------------------------------------------------
            # OPTION VALUES
            # -------------------------------------------------

            values = self.CATEGORY_OPTIONS.get(
                category.name,
                {},
            ).get(
                category_option.name,
                [],
            )

            for value_sort_order, value_name in enumerate(
                values,
                start=1,
            ):
                value, _ = (
                    ProductOptionValue.objects.get_or_create(
                        option=option,
                        slug=slugify(value_name),
                        defaults={
                            "name": value_name,
                            "sort_order": value_sort_order,
                            "is_active": True,
                        },
                    )
                )

                updates = []

                if value.name != value_name:
                    value.name = value_name
                    updates.append("name")

                if value.sort_order != value_sort_order:
                    value.sort_order = value_sort_order
                    updates.append("sort_order")

                if not value.is_active:
                    value.is_active = True
                    updates.append("is_active")

                if updates:
                    value.save(
                        update_fields=updates
                    )

        return product_options

    # =========================================================
    # ENSURE PRODUCT VARIANTS
    # =========================================================

    def ensure_product_variants(
        self,
        product,
        category,
    ):
        """
        Ensure an existing product has the expected variant structure.

        Existing valid variants are retained.

        If no variants exist, the complete variant set is generated.
        """

        existing_variants = list(
            product.variants.all()
        )

        if existing_variants:
            return self.reconcile_variant_images(
                product=product,
                variants=existing_variants,
            )

        return self.create_product_variants(
            product=product,
            category=category,
            product_number=product.sort_order,
        )

    # =========================================================
    # CREATE VARIANTS
    # =========================================================

    def create_product_variants(
        self,
        product,
        category,
        product_number,
    ):
        product_options = self.create_product_options(
            product=product,
            category=category,
        )

        # -----------------------------------------------------
        # REQUIRE AT LEAST TWO OPTIONS
        # -----------------------------------------------------

        if len(product_options) < 2:
            raise ValueError(
                f"Variant product '{product.name}' must have at least "
                f"two ProductOptions. Category '{category.name}' only "
                f"has {len(product_options)}."
            )

        # -----------------------------------------------------
        # GET OPTION VALUES
        # -----------------------------------------------------

        option_values = []

        for option in product_options:
            values = list(
                option.active_values.order_by(
                    "sort_order",
                    "created_at",
                )[:3]
            )

            if len(values) < 2:
                raise ValueError(
                    f"ProductOption '{option.name}' for "
                    f"'{product.name}' needs at least two values."
                )

            option_values.append(values)

        # -----------------------------------------------------
        # COMBINATIONS
        # -----------------------------------------------------

        combinations = list(
            cartesian_product(*option_values)
        )[:self.VARIANTS_PER_PRODUCT]

        if len(combinations) != self.VARIANTS_PER_PRODUCT:
            raise ValueError(
                f"Unable to create "
                f"{self.VARIANTS_PER_PRODUCT} variants for "
                f"'{product.name}'."
            )

        # -----------------------------------------------------
        # PRICE ADJUSTMENTS
        # -----------------------------------------------------

        price_adjustments = [
            Decimal("0"),
            Decimal("5000"),
            Decimal("10000"),
            Decimal("15000"),
            Decimal("20000"),
            Decimal("25000"),
        ]

        # -----------------------------------------------------
        # PREPARE VARIANTS
        # -----------------------------------------------------

        variants = []

        for variant_index, selected_values in enumerate(
            combinations,
            start=1,
        ):
            value_names = [
                value.name
                for value in selected_values
            ]

            variant_name = " / ".join(
                value_names
            )

            variant_sku = (
                f"{product.sku}-"
                f"V{variant_index:02d}"
            )

            variant_price = (
                product.price
                + price_adjustments[
                    variant_index - 1
                ]
            )

            variant_compare_at_price = (
                variant_price * Decimal("1.15")
            ).quantize(
                Decimal("0.01")
            )

            variants.append(
                ProductVariant(
                    product=product,
                    name=variant_name,
                    sku=variant_sku,
                    price=variant_price,
                    compare_at_price=(
                        variant_compare_at_price
                    ),
                    stock_quantity=self.random.randint(
                        5,
                        50,
                    ),
                    track_inventory=True,
                    weight=Decimal(
                        str(
                            self.random.randint(
                                200,
                                2500,
                            )
                        )
                    ),
                    is_active=True,
                    is_default=(
                        variant_index == 1
                    ),
                    is_available=True,
                    sort_order=variant_index,
                )
            )

        # -----------------------------------------------------
        # DATABASE TRANSACTION
        # -----------------------------------------------------

        uploaded_results = {}

        try:
            with transaction.atomic():

                ProductVariant.objects.bulk_create(
                    variants,
                    batch_size=100,
                )

                # -------------------------------------------------
                # VARIANT OPTION RELATIONSHIPS
                # -------------------------------------------------

                variant_option_values = []

                for variant, selected_values in zip(
                    variants,
                    combinations,
                ):
                    for selected_value in selected_values:
                        variant_option_values.append(
                            ProductVariantOptionValue(
                                variant=variant,
                                option_value=selected_value,
                            )
                        )

                ProductVariantOptionValue.objects.bulk_create(
                    variant_option_values,
                    batch_size=500,
                )

                # -------------------------------------------------
                # PREPARE IMAGE JOBS
                # -------------------------------------------------

                image_jobs = (
                    self.prepare_image_jobs(
                        product=product,
                        variants=variants,
                        combinations=combinations,
                    )
                )

                # -------------------------------------------------
                # CLOUDINARY UPLOAD
                # -------------------------------------------------

                uploaded_results = (
                    self.upload_images_concurrently(
                        image_jobs
                    )
                )

                # -------------------------------------------------
                # IMAGE DATABASE RECORDS
                # -------------------------------------------------

                image_records = []

                for job in image_jobs:
                    result = uploaded_results.get(
                        job["public_id"]
                    )

                    if not result:
                        raise RuntimeError(
                            "Missing Cloudinary upload result "
                            f"for '{job['public_id']}'."
                        )

                    cloudinary_public_id = result.get(
                        "public_id"
                    )

                    if not cloudinary_public_id:
                        raise RuntimeError(
                            "Cloudinary upload succeeded but no "
                            "public_id was returned for "
                            f"'{job['public_id']}'."
                        )

                    image_records.append(
                        ProductVariantImage(
                            variant=job["variant"],
                            image=cloudinary_public_id,
                            alt_text=(
                                f"{product.name} - "
                                f"{job['variant_name']} - "
                                f"Image {job['image_index']}"
                            ),
                            is_primary=(
                                job["image_index"] == 1
                            ),
                            display_order=(
                                job["image_index"]
                            ),
                            is_active=True,
                        )
                    )

                # -------------------------------------------------
                # BULK IMAGE INSERT
                # -------------------------------------------------

                ProductVariantImage.objects.bulk_create(
                    image_records,
                    batch_size=500,
                )

                # -------------------------------------------------
                # SET PRIMARY IMAGE FIELD
                # -------------------------------------------------

                primary_images = {}

                for image in image_records:
                    if image.is_primary:
                        primary_images[
                            image.variant_id
                        ] = image

                for variant in variants:
                    primary_image = primary_images.get(
                        variant.id
                    )

                    if primary_image:
                        variant.productvariantimage_id = (
                            primary_image.pk
                        )

                # -------------------------------------------------
                # UPDATE VARIANTS
                # -------------------------------------------------

                ProductVariant.objects.bulk_update(
                    variants,
                    [
                        "productvariantimage",
                        "updated_at",
                    ],
                    batch_size=100,
                )

        except Exception:
            # -----------------------------------------------------
            # IMPORTANT:
            #
            # Django rolls back the database transaction, but it
            # cannot roll back Cloudinary.
            #
            # Therefore all successfully uploaded assets must be
            # explicitly removed when database creation fails.
            # -----------------------------------------------------

            self.cleanup_uploaded_images(
                uploaded_results
            )

            raise

        return (
            len(variants),
            len(image_records),
        )

    # =========================================================
    # PREPARE IMAGE JOBS
    # =========================================================

    def prepare_image_jobs(
        self,
        product,
        variants,
        combinations,
    ):
        """
        Prepare all SVG/image jobs before starting network uploads.
        """

        image_jobs = []

        for variant_index, (
            variant,
            selected_values,
        ) in enumerate(
            zip(
                variants,
                combinations,
            ),
            start=1,
        ):
            variant_name = " / ".join(
                value.name
                for value in selected_values
            )

            for image_index in range(
                1,
                self.IMAGES_PER_VARIANT + 1,
            ):
                background = self.random.choice(
                    self.IMAGE_BACKGROUNDS
                )

                svg = self.build_variant_svg(
                    product_name=product.name,
                    variant_name=variant_name,
                    variant_index=variant_index,
                    image_index=image_index,
                    background=background,
                )

                public_id = (
                    f"{self.CLOUDINARY_FOLDER}/"
                    f"{product.id}/"
                    f"variant-{variant.id}/"
                    f"image-{image_index}"
                )

                image_jobs.append(
                    {
                        "variant": variant,
                        "variant_index": variant_index,
                        "image_index": image_index,
                        "variant_name": variant_name,
                        "svg": svg,
                        "public_id": public_id,
                    }
                )

        return image_jobs

    # =========================================================
    # RECONCILE VARIANT IMAGES
    # =========================================================

    def reconcile_variant_images(
        self,
        product,
        variants,
    ):
        """
        Repair image state for existing variants.

        Existing image records are retained. Missing gallery images
        are uploaded and created.
        """

        total_variants = len(variants)
        total_images = 0

        image_jobs = []

        for variant_index, variant in enumerate(
            variants,
            start=1,
        ):
            existing_images = {
                image.display_order: image
                for image in variant.images.all()
            }

            variant_name = variant.name

            for image_index in range(
                1,
                self.IMAGES_PER_VARIANT + 1,
            ):
                existing_image = existing_images.get(
                    image_index
                )

                if existing_image:
                    continue

                background = self.random.choice(
                    self.IMAGE_BACKGROUNDS
                )

                svg = self.build_variant_svg(
                    product_name=product.name,
                    variant_name=variant_name,
                    variant_index=variant_index,
                    image_index=image_index,
                    background=background,
                )

                public_id = (
                    f"{self.CLOUDINARY_FOLDER}/"
                    f"{product.id}/"
                    f"variant-{variant.id}/"
                    f"image-{image_index}"
                )

                image_jobs.append(
                    {
                        "variant": variant,
                        "variant_index": variant_index,
                        "image_index": image_index,
                        "variant_name": variant_name,
                        "svg": svg,
                        "public_id": public_id,
                    }
                )

        if image_jobs:
            uploaded_results = {}

            try:
                uploaded_results = (
                    self.upload_images_concurrently(
                        image_jobs
                    )
                )

                image_records = []

                for job in image_jobs:
                    result = uploaded_results.get(
                        job["public_id"]
                    )

                    if not result:
                        raise RuntimeError(
                            "Missing Cloudinary upload result "
                            f"for '{job['public_id']}'."
                        )

                    public_id = result.get(
                        "public_id"
                    )

                    if not public_id:
                        raise RuntimeError(
                            "Cloudinary upload returned no "
                            f"public_id for '{job['public_id']}'."
                        )

                    image_records.append(
                        ProductVariantImage(
                            variant=job["variant"],
                            image=public_id,
                            alt_text=(
                                f"{product.name} - "
                                f"{job['variant_name']} - "
                                f"Image {job['image_index']}"
                            ),
                            is_primary=(
                                job["image_index"] == 1
                            ),
                            display_order=(
                                job["image_index"]
                            ),
                            is_active=True,
                        )
                    )

                with transaction.atomic():
                    ProductVariantImage.objects.bulk_create(
                        image_records,
                        batch_size=500,
                    )

                    total_images += len(
                        image_records
                    )

            except Exception:
                self.cleanup_uploaded_images(
                    uploaded_results
                )

                raise

        # -----------------------------------------------------
        # REPAIR PRIMARY IMAGE REFERENCES
        # -----------------------------------------------------

        self.repair_primary_variant_images(
            variants
        )

        return (
            total_variants,
            total_images,
        )

    # =========================================================
    # REPAIR PRIMARY IMAGE REFERENCES
    # =========================================================

    def repair_primary_variant_images(
        self,
        variants,
    ):
        """
        Ensure every variant points to its image #1 as its
        primary ProductVariantImage.
        """

        variants_to_update = []

        for variant in variants:
            primary_image = (
                ProductVariantImage.objects
                .filter(
                    variant=variant,
                    display_order=1,
                    is_active=True,
                )
                .order_by("created_at")
                .first()
            )

            if not primary_image:
                continue

            if (
                variant.productvariantimage_id
                != primary_image.pk
            ):
                variant.productvariantimage_id = (
                    primary_image.pk
                )

                variants_to_update.append(
                    variant
                )

        if variants_to_update:
            ProductVariant.objects.bulk_update(
                variants_to_update,
                [
                    "productvariantimage",
                    "updated_at",
                ],
                batch_size=100,
            )

    # =========================================================
    # BUILD VARIANT SVG
    # =========================================================

    def build_variant_svg(
        self,
        product_name,
        variant_name,
        variant_index,
        image_index,
        background,
    ):
        safe_product_name = escape(
            str(product_name)
        )

        safe_variant_name = escape(
            str(variant_name)
        )

        image_labels = {
            1: "PRIMARY",
            2: "GALLERY",
            3: "DETAIL",
            4: "ALTERNATE",
            5: "VIEW",
        }

        image_label = image_labels.get(
            image_index,
            "GALLERY",
        )

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="1000"
    height="1000"
    viewBox="0 0 1000 1000"
>
    <rect
        width="1000"
        height="1000"
        fill="{background}"
    />

    <rect
        x="80"
        y="80"
        width="840"
        height="840"
        rx="40"
        fill="#FFFFFF"
        stroke="#D1D5DB"
        stroke-width="4"
    />

    <circle
        cx="500"
        cy="330"
        r="150"
        fill="{background}"
        stroke="#9CA3AF"
        stroke-width="5"
    />

    <text
        x="500"
        y="310"
        text-anchor="middle"
        font-family="Arial, Helvetica, sans-serif"
        font-size="42"
        font-weight="700"
        fill="#111827"
    >
        MOCK
    </text>

    <text
        x="500"
        y="375"
        text-anchor="middle"
        font-family="Arial, Helvetica, sans-serif"
        font-size="28"
        fill="#374151"
    >
        PRODUCT
    </text>

    <text
        x="500"
        y="590"
        text-anchor="middle"
        font-family="Arial, Helvetica, sans-serif"
        font-size="36"
        font-weight="700"
        fill="#111827"
    >
        {safe_product_name}
    </text>

    <text
        x="500"
        y="650"
        text-anchor="middle"
        font-family="Arial, Helvetica, sans-serif"
        font-size="28"
        fill="#4B5563"
    >
        {safe_variant_name}
    </text>

    <text
        x="500"
        y="715"
        text-anchor="middle"
        font-family="Arial, Helvetica, sans-serif"
        font-size="22"
        fill="#6B7280"
    >
        {image_label}
    </text>

    <text
        x="500"
        y="755"
        text-anchor="middle"
        font-family="Arial, Helvetica, sans-serif"
        font-size="20"
        fill="#9CA3AF"
    >
        Variant {variant_index} · Image {image_index}
    </text>
</svg>
"""

    # =========================================================
    # UPLOAD IMAGES CONCURRENTLY
    # =========================================================

    def upload_images_concurrently(
        self,
        image_jobs,
    ):
        """
        Upload all image jobs concurrently.

        Only network-bound Cloudinary work happens inside the worker
        threads. Django ORM operations remain in the main thread.
        """

        results = {}

        if not image_jobs:
            return results

        worker_count = min(
            self.CLOUDINARY_WORKERS,
            len(image_jobs),
        )

        self.stdout.write(
            f"    Uploading {len(image_jobs)} Cloudinary images "
            f"using {worker_count} workers..."
        )

        successful = 0

        with ThreadPoolExecutor(
            max_workers=worker_count
        ) as executor:

            future_map = {
                executor.submit(
                    self.upload_single_image,
                    job,
                ): job
                for job in image_jobs
            }

            for future in as_completed(
                future_map
            ):
                job = future_map[future]

                try:
                    result = future.result()

                except Exception:
                    # Cancel jobs that have not started.
                    for pending_future in future_map:
                        pending_future.cancel()

                    # Remove assets already uploaded.
                    self.cleanup_uploaded_images(
                        results
                    )

                    raise

                results[
                    job["public_id"]
                ] = result

                successful += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"    Cloudinary uploads completed: "
                f"{successful}/{len(image_jobs)}"
            )
        )

        return results

    # =========================================================
    # UPLOAD SINGLE IMAGE
    # =========================================================

    def upload_single_image(
        self,
        job,
    ):
        """
        Upload exactly one SVG asset to Cloudinary.

        Every gallery image has its own deterministic public ID.
        """

        return cloudinary.uploader.upload(
            job["svg"].encode("utf-8"),
            public_id=job["public_id"],
            resource_type="image",
            format="svg",
            overwrite=self.CLOUDINARY_OVERWRITE,
            tags=[
                "mock-product",
                f"variant-{job['variant'].id}",
                f"gallery-image-{job['image_index']}",
            ],
        )

    # =========================================================
    # CLEAN UP UPLOADED IMAGES
    # =========================================================

    def cleanup_uploaded_images(
        self,
        upload_results,
    ):
        """
        Remove Cloudinary assets uploaded by the current operation.

        This is necessary because database transactions cannot
        automatically roll back Cloudinary uploads.
        """

        if not upload_results:
            return

        self.stdout.write(
            self.style.WARNING(
                "Cleaning up partially uploaded Cloudinary images..."
            )
        )

        for result in upload_results.values():
            public_id = result.get(
                "public_id"
            )

            if not public_id:
                continue

            try:
                cloudinary.uploader.destroy(
                    public_id,
                    resource_type="image",
                )

            except Exception as exc:
                self.stdout.write(
                    self.style.WARNING(
                        "Could not delete Cloudinary asset "
                        f"'{public_id}': {exc}"
                    )
                )

    # =========================================================
    # STORE OPERATING HOURS
    # =========================================================

    def create_store_operating_hours(
        self,
        store,
    ):
        """
        Create/update all seven days for a store.

        Safe to run repeatedly.
        """

        for weekday, hours in self.STORE_HOURS.items():
            opens_at, closes_at = hours

            if opens_at is None:
                defaults = {
                    "is_closed": True,
                    "opens_at": None,
                    "closes_at": None,
                    "pickup_available": False,
                    "notes": (
                        "Store closed on Sunday."
                    ),
                }

            else:
                defaults = {
                    "is_closed": False,
                    "opens_at": opens_at,
                    "closes_at": closes_at,
                    "pickup_available": True,
                    "notes": (
                        "Regular store operating hours."
                    ),
                }

            StoreOperatingHour.objects.update_or_create(
                store=store,
                weekday=weekday,
                defaults=defaults,
            )

    # =========================================================
    # PRODUCT SUMMARY
    # =========================================================

    def get_product_summary(self):
        return {
            "variant_products": len(
                self.VARIANT_PRODUCTS
            ),
            "non_variant_products": len(
                self.NON_VARIANT_PRODUCTS
            ),
            "products_per_store": (
                len(self.VARIANT_PRODUCTS)
                + len(self.NON_VARIANT_PRODUCTS)
            ),
            "variants_per_product": (
                self.VARIANTS_PER_PRODUCT
            ),
            "images_per_variant": (
                self.IMAGES_PER_VARIANT
            ),
        }
