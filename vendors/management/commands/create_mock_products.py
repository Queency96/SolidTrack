import random
from datetime import time
from decimal import Decimal
from html import escape
from itertools import product as cartesian_product

from django.core.files.base import ContentFile
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

    # ---------------------------------------------------------
    # CONFIGURATION
    # ---------------------------------------------------------

    DEFAULT_PRODUCTS_PER_STORE = 30
    DEFAULT_VARIANT_PRODUCTS = 20
    DEFAULT_NON_VARIANT_PRODUCTS = 10

    VARIANTS_PER_PRODUCT = 6

    MOCK_VENDOR_DOMAIN = "@soliddistributor.com"

    RANDOM_SEED = 20260915

    # ---------------------------------------------------------
    # PRODUCT DEFINITIONS
    # ---------------------------------------------------------
    #
    # Each definition contains:
    #   name
    #   category
    #   price
    #   short_description
    #   description
    #
    # Variant products additionally use the category's
    # CategoryOption definitions below.
    #
    # ---------------------------------------------------------

    VARIANT_PRODUCTS = [
        {
            "name": "Apple iPhone 15",
            "category": "Smartphones",
            "price": Decimal("850000"),
            "short_description": "Premium Apple smartphone with advanced camera system.",
            "description": (
                "Apple iPhone 15 with a modern design, powerful performance, "
                "excellent cameras and all-day battery life."
            ),
        },
        {
            "name": "Samsung Galaxy S24",
            "category": "Smartphones",
            "price": Decimal("920000"),
            "short_description": "Flagship Samsung smartphone with premium performance.",
            "description": (
                "Samsung Galaxy S24 featuring a high-resolution display, "
                "powerful processor and advanced camera capabilities."
            ),
        },
        {
            "name": "Google Pixel 9",
            "category": "Smartphones",
            "price": Decimal("880000"),
            "short_description": "Google smartphone with intelligent camera features.",
            "description": (
                "Google Pixel 9 delivers clean Android software, "
                "excellent photography and smooth everyday performance."
            ),
        },
        {
            "name": "Apple MacBook Air",
            "category": "Laptops",
            "price": Decimal("1450000"),
            "short_description": "Slim and powerful Apple laptop for work and study.",
            "description": (
                "Apple MacBook Air designed for productivity, portability "
                "and everyday professional computing."
            ),
        },
        {
            "name": "Dell XPS 15",
            "category": "Laptops",
            "price": Decimal("1650000"),
            "short_description": "Premium Dell laptop for demanding workloads.",
            "description": (
                "Dell XPS 15 combines premium construction, strong performance "
                "and a high-quality display."
            ),
        },
        {
            "name": "HP Spectre x360",
            "category": "Laptops",
            "price": Decimal("1550000"),
            "short_description": "Convertible premium HP laptop.",
            "description": (
                "HP Spectre x360 is a versatile convertible laptop "
                "for productivity, creativity and entertainment."
            ),
        },
        {
            "name": "Lenovo ThinkPad X1 Carbon",
            "category": "Laptops",
            "price": Decimal("1750000"),
            "short_description": "Business-focused Lenovo laptop.",
            "description": (
                "Lenovo ThinkPad X1 Carbon provides business-class "
                "performance, portability and durability."
            ),
        },
        {
            "name": "Samsung 55-inch Smart TV",
            "category": "Televisions",
            "price": Decimal("780000"),
            "short_description": "55-inch Samsung smart television.",
            "description": (
                "Samsung Smart TV with a large high-quality display, "
                "smart streaming features and immersive entertainment."
            ),
        },
        {
            "name": "LG 55-inch OLED TV",
            "category": "Televisions",
            "price": Decimal("1100000"),
            "short_description": "Premium LG OLED television.",
            "description": (
                "LG OLED TV delivers deep blacks, vibrant colours "
                "and an immersive home entertainment experience."
            ),
        },
        {
            "name": "Sony Bravia 55-inch TV",
            "category": "Televisions",
            "price": Decimal("980000"),
            "short_description": "Sony Bravia smart television.",
            "description": (
                "Sony Bravia television with excellent picture quality, "
                "smart features and premium sound support."
            ),
        },
        {
            "name": "Apple AirPods Pro",
            "category": "Audio",
            "price": Decimal("390000"),
            "short_description": "Premium wireless earbuds with noise cancellation.",
            "description": (
                "Apple AirPods Pro provide immersive sound, active noise "
                "cancellation and a compact wireless design."
            ),
        },
        {
            "name": "Sony WH-1000XM5",
            "category": "Audio",
            "price": Decimal("520000"),
            "short_description": "Premium wireless noise-cancelling headphones.",
            "description": (
                "Sony WH-1000XM5 headphones provide high-quality sound "
                "and advanced active noise cancellation."
            ),
        },
        {
            "name": "JBL Charge 5",
            "category": "Audio",
            "price": Decimal("210000"),
            "short_description": "Portable JBL Bluetooth speaker.",
            "description": (
                "JBL Charge 5 delivers powerful portable audio "
                "with long battery life."
            ),
        },
        {
            "name": "Apple Watch Series 10",
            "category": "Wearables",
            "price": Decimal("520000"),
            "short_description": "Modern Apple smartwatch.",
            "description": (
                "Apple Watch Series 10 combines health, fitness, "
                "communication and smart features."
            ),
        },
        {
            "name": "Samsung Galaxy Watch 7",
            "category": "Wearables",
            "price": Decimal("390000"),
            "short_description": "Samsung smartwatch with health tracking.",
            "description": (
                "Galaxy Watch 7 provides fitness tracking, notifications, "
                "health monitoring and smart functionality."
            ),
        },
        {
            "name": "Nike Air Max",
            "category": "Shoes",
            "price": Decimal("180000"),
            "short_description": "Comfortable Nike lifestyle sneakers.",
            "description": (
                "Nike Air Max sneakers designed for everyday comfort, "
                "style and casual activities."
            ),
        },
        {
            "name": "Adidas Ultraboost",
            "category": "Shoes",
            "price": Decimal("210000"),
            "short_description": "Performance running shoes from Adidas.",
            "description": (
                "Adidas Ultraboost running shoes designed for responsive "
                "cushioning and everyday running."
            ),
        },
        {
            "name": "PlayStation 5 Slim",
            "category": "Gaming",
            "price": Decimal("850000"),
            "short_description": "Sony PlayStation 5 Slim gaming console.",
            "description": (
                "PlayStation 5 Slim delivers next-generation gaming "
                "performance with a compact console design."
            ),
        },
        {
            "name": "Xbox Series X",
            "category": "Gaming",
            "price": Decimal("780000"),
            "short_description": "Microsoft Xbox Series X console.",
            "description": (
                "Xbox Series X provides high-performance gaming, "
                "fast loading and 4K gaming capabilities."
            ),
        },
        {
            "name": "Nintendo Switch OLED",
            "category": "Gaming",
            "price": Decimal("480000"),
            "short_description": "Nintendo hybrid gaming console.",
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
            "short_description": "Durable USB-C fast charging cable.",
            "description": "High-quality USB-C cable suitable for charging and data transfer.",
        },
        {
            "name": "65W USB-C Charger",
            "category": "Accessories",
            "price": Decimal("35000"),
            "short_description": "Compact 65W USB-C power adapter.",
            "description": "Fast USB-C charger suitable for phones, tablets and compatible laptops.",
        },
        {
            "name": "Wireless Mouse",
            "category": "Computer Accessories",
            "price": Decimal("22000"),
            "short_description": "Comfortable wireless computer mouse.",
            "description": "Reliable wireless mouse for office, school and home computing.",
        },
        {
            "name": "Laptop Backpack",
            "category": "Bags",
            "price": Decimal("45000"),
            "short_description": "Protective laptop backpack.",
            "description": "Spacious laptop backpack with multiple compartments.",
        },
        {
            "name": "Power Bank 20000mAh",
            "category": "Accessories",
            "price": Decimal("50000"),
            "short_description": "High-capacity portable power bank.",
            "description": "20,000mAh portable battery for charging compatible devices on the go.",
        },
        {
            "name": "Tempered Glass Screen Protector",
            "category": "Accessories",
            "price": Decimal("10000"),
            "short_description": "Protective tempered glass screen protector.",
            "description": "Durable tempered glass designed to protect smartphone displays.",
        },
        {
            "name": "Bluetooth USB Adapter",
            "category": "Computer Accessories",
            "price": Decimal("12000"),
            "short_description": "Compact Bluetooth adapter for computers.",
            "description": "USB Bluetooth adapter for connecting compatible wireless devices.",
        },
        {
            "name": "HDMI Cable",
            "category": "Computer Accessories",
            "price": Decimal("10000"),
            "short_description": "High-speed HDMI cable.",
            "description": "HDMI cable suitable for televisions, monitors, consoles and computers.",
        },
        {
            "name": "Laptop Stand",
            "category": "Computer Accessories",
            "price": Decimal("30000"),
            "short_description": "Adjustable ergonomic laptop stand.",
            "description": "Adjustable stand designed to improve laptop viewing height and ergonomics.",
        },
        {
            "name": "Smartphone Tripod",
            "category": "Accessories",
            "price": Decimal("28000"),
            "short_description": "Adjustable smartphone tripod.",
            "description": "Compact tripod for photography, video recording and online meetings.",
        },
    ]

    # ---------------------------------------------------------
    # CATEGORY OPTIONS
    # ---------------------------------------------------------
    #
    # These are created as CategoryOption records and then
    # copied to ProductOption for each variant product.
    #
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # STORE OPERATING HOURS
    # ---------------------------------------------------------

    STORE_HOURS = {
        0: (time(8, 0), time(18, 0)),   # Monday
        1: (time(8, 0), time(18, 0)),   # Tuesday
        2: (time(8, 0), time(18, 0)),   # Wednesday
        3: (time(8, 0), time(18, 0)),   # Thursday
        4: (time(8, 0), time(18, 0)),   # Friday
        5: (time(9, 0), time(17, 0)),   # Saturday
        6: (None, None),                # Sunday
    }

    # ---------------------------------------------------------
    # COLORS USED FOR GENERATED SVG IMAGES
    # ---------------------------------------------------------

    IMAGE_BACKGROUNDS = [
        "#F4F4F5",
        "#E5E7EB",
        "#DBEAFE",
        "#DCFCE7",
        "#FEF3C7",
        "#FCE7F3",
        "#EDE9FE",
    ]

    # ---------------------------------------------------------
    # COMMAND
    # ---------------------------------------------------------

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Delete existing mock products before creating them.",
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

    # ---------------------------------------------------------
    # HANDLE
    # ---------------------------------------------------------

    def handle(self, *args, **options):
        self.random = random.Random(self.RANDOM_SEED)

        overwrite = options["overwrite"]
        all_vendors = options["all_vendors"]
        stores_per_vendor = options["stores_per_vendor"]

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Starting mock product generation..."
            )
        )
        self.stdout.write("")

        if len(self.VARIANT_PRODUCTS) != self.DEFAULT_VARIANT_PRODUCTS:
            raise ValueError(
                f"Expected {self.DEFAULT_VARIANT_PRODUCTS} variant "
                f"product definitions, found {len(self.VARIANT_PRODUCTS)}."
            )

        if len(self.NON_VARIANT_PRODUCTS) != self.DEFAULT_NON_VARIANT_PRODUCTS:
            raise ValueError(
                f"Expected {self.DEFAULT_NON_VARIANT_PRODUCTS} non-variant "
                f"product definitions, found {len(self.NON_VARIANT_PRODUCTS)}."
            )

        if overwrite:
            self.delete_mock_products()

        categories = self.create_categories()

        vendors = self.get_vendors(all_vendors=all_vendors)

        if not vendors.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No vendors found."
                )
            )
            return

        total_products = 0
        total_variants = 0
        total_images = 0
        total_stores = 0

        for vendor in vendors:
            stores = vendor.stores.all().order_by("created_at")

            if stores_per_vendor is not None:
                if stores_per_vendor <= 0:
                    raise ValueError(
                        "--stores-per-vendor must be greater than zero."
                    )

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
                products_created, variants_created, images_created = (
                    self.create_products_for_store(
                        vendor=vendor,
                        store=store,
                        categories=categories,
                    )
                )

                self.create_store_operating_hours(store)

                total_products += products_created
                total_variants += variants_created
                total_images += images_created
                total_stores += 1

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

    # ---------------------------------------------------------
    # VENDORS
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # DELETE MOCK PRODUCTS
    # ---------------------------------------------------------

    def delete_mock_products(self):
        self.stdout.write(
            self.style.WARNING(
                "Deleting existing mock products..."
            )
        )

        deleted_count, _ = Product.objects.filter(
            sku__startswith="MOCK-"
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} mock product-related records."
            )
        )

    # ---------------------------------------------------------
    # CATEGORIES
    # ---------------------------------------------------------

    def create_categories(self):
        category_names = set()

        for item in self.VARIANT_PRODUCTS:
            category_names.add(item["category"])

        for item in self.NON_VARIANT_PRODUCTS:
            category_names.add(item["category"])

        categories = {}

        for sort_order, category_name in enumerate(
            sorted(category_names),
            start=1,
        ):
            category, _ = ProductCategory.objects.get_or_create(
                slug=slugify(category_name),
                defaults={
                    "name": category_name,
                    "description": (
                        f"Mock product category for {category_name}."
                    ),
                    "sort_order": sort_order,
                    "is_active": True,
                },
            )

            # Update the name if the category already exists.
            changed = False

            if category.name != category_name:
                category.name = category_name
                changed = True

            if not category.is_active:
                category.is_active = True
                changed = True

            if changed:
                category.save()

            categories[category_name] = category

            # Create CategoryOption records for categories that
            # support variants.
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

                changed = False

                if category_option.name != option_name:
                    category_option.name = option_name
                    changed = True

                if category_option.sort_order != option_sort_order:
                    category_option.sort_order = option_sort_order
                    changed = True

                if not category_option.is_active:
                    category_option.is_active = True
                    changed = True

                if changed:
                    category_option.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Categories ready: {len(categories)}"
            )
        )

        return categories

    # ---------------------------------------------------------
    # CREATE PRODUCTS FOR STORE
    # ---------------------------------------------------------

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

        # -----------------------------------------------------
        # VARIANT PRODUCTS
        # -----------------------------------------------------

        for index, definition in enumerate(
            self.VARIANT_PRODUCTS,
            start=1,
        ):
            product_result = self.create_product(
                vendor=vendor,
                store=store,
                category=categories[definition["category"]],
                definition=definition,
                product_number=index,
                is_variant_product=True,
            )

            if product_result is None:
                continue

            product_created, product_variant_count, image_count = (
                product_result
            )

            if product_created:
                products_created += 1

            variants_created += product_variant_count
            images_created += image_count

        # -----------------------------------------------------
        # NON-VARIANT PRODUCTS
        # -----------------------------------------------------

        non_variant_start = len(self.VARIANT_PRODUCTS) + 1

        for offset, definition in enumerate(
            self.NON_VARIANT_PRODUCTS,
            start=0,
        ):
            product_result = self.create_product(
                vendor=vendor,
                store=store,
                category=categories[definition["category"]],
                definition=definition,
                product_number=non_variant_start + offset,
                is_variant_product=False,
            )

            if product_result is None:
                continue

            product_created, product_variant_count, image_count = (
                product_result
            )

            if product_created:
                products_created += 1

            variants_created += product_variant_count
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

    # ---------------------------------------------------------
    # CREATE PRODUCT
    # ---------------------------------------------------------

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
            f"{vendor.id.hex[:8].upper()}-"
            f"{store.id.hex[:8].upper()}-"
            f"P{product_number:02d}"
        )

        # -----------------------------------------------------
        # IDPOTENCY
        # -----------------------------------------------------
        #
        # If the product already exists, do not duplicate it.
        #
        # -----------------------------------------------------

        existing_product = Product.objects.filter(
            vendor=vendor,
            sku=product_sku,
        ).first()

        if existing_product:
            return None

        compare_at_price = (
            definition["price"] * Decimal("1.15")
        ).quantize(
            Decimal("0.01")
        )

        with transaction.atomic():
            product = Product.objects.create(
                vendor=vendor,
                store=store,
                category=category,
                name=product_name,
                slug=product_slug,
                sku=product_sku,
                short_description=definition[
                    "short_description"
                ],
                description=definition[
                    "description"
                ],
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
                variant_count, image_count = (
                    self.create_product_variants(
                        product=product,
                        category=category,
                        product_number=product_number,
                    )
                )
            else:
                variant_count = 0
                image_count = 0

        return (
            True,
            variant_count,
            image_count,
        )

    # ---------------------------------------------------------
    # CREATE PRODUCT OPTIONS
    # ---------------------------------------------------------

    def create_product_options(
        self,
        product,
        category,
    ):
        category_option_queryset = (
            category.category_options
            .filter(is_active=True)
            .order_by("sort_order", "created_at")
        )

        product_options = []

        for category_option in category_option_queryset:
            option, _ = ProductOption.objects.get_or_create(
                product=product,
                slug=category_option.slug,
                defaults={
                    "name": category_option.name,
                    "sort_order": category_option.sort_order,
                    "is_active": True,
                },
            )

            changed = False

            if option.name != category_option.name:
                option.name = category_option.name
                changed = True

            if option.sort_order != category_option.sort_order:
                option.sort_order = category_option.sort_order
                changed = True

            if not option.is_active:
                option.is_active = True
                changed = True

            if changed:
                option.save()

            product_options.append(option)

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
                ProductOptionValue.objects.get_or_create(
                    option=option,
                    slug=slugify(value_name),
                    defaults={
                        "name": value_name,
                        "sort_order": value_sort_order,
                        "is_active": True,
                    },
                )

        return product_options

    # ---------------------------------------------------------
    # CREATE VARIANTS
    # ---------------------------------------------------------

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

        if len(product_options) < 2:
            raise ValueError(
                f"Variant product '{product.name}' must have at "
                f"least two ProductOptions. "
                f"Category '{category.name}' only has "
                f"{len(product_options)}."
            )

        # -----------------------------------------------------
        # Get values for each product option
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
        # Create combinations.
        #
        # For two options with three values each:
        #
        #   3 × 3 = 9 combinations
        #
        # We only create the first six combinations because
        # the requirement is six variants per variant product.
        # -----------------------------------------------------

        combinations = list(
            cartesian_product(*option_values)
        )[: self.VARIANTS_PER_PRODUCT]

        if len(combinations) != self.VARIANTS_PER_PRODUCT:
            raise ValueError(
                f"Unable to create {self.VARIANTS_PER_PRODUCT} "
                f"variants for '{product.name}'."
            )

        variant_count = 0
        image_count = 0

        for variant_index, selected_values in enumerate(
            combinations,
            start=1,
        ):
            value_names = [
                value.name
                for value in selected_values
            ]

            variant_name = " / ".join(value_names)

            variant_sku = (
                f"{product.sku}-"
                f"V{variant_index:02d}"
            )

            base_price = product.price

            # Give different combinations slightly different
            # prices while keeping them deterministic.
            price_adjustments = [
                Decimal("0"),
                Decimal("5000"),
                Decimal("10000"),
                Decimal("15000"),
                Decimal("20000"),
                Decimal("25000"),
            ]

            variant_price = (
                base_price
                + price_adjustments[
                    variant_index - 1
                ]
            )

            variant_compare_at_price = (
                variant_price
                * Decimal("1.15")
            ).quantize(
                Decimal("0.01")
            )

            variant = ProductVariant.objects.create(
                product=product,
                name=variant_name,
                sku=variant_sku,
                price=variant_price,
                compare_at_price=variant_compare_at_price,
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

            # -------------------------------------------------
            # Attach ProductOptionValue records to the variant
            # through ProductVariantOptionValue.
            # -------------------------------------------------

            for selected_value in selected_values:
                ProductVariantOptionValue.objects.create(
                    variant=variant,
                    option_value=selected_value,
                )

            # -------------------------------------------------
            # Create actual image content.
            #
            # This is a generated SVG image uploaded through
            # your CloudinaryField.
            # -------------------------------------------------

            image = self.create_variant_image(
                variant=variant,
                product_name=product.name,
                variant_name=variant_name,
                variant_index=variant_index,
            )

            # -------------------------------------------------
            # ProductVariant.productvariantimage
            #
            # Your model has this exact field name.
            # -------------------------------------------------

            variant.productvariantimage = image

            variant.save(
                update_fields=[
                    "productvariantimage",
                    "updated_at",
                ]
            )

            variant_count += 1
            image_count += 1

        return (
            variant_count,
            image_count,
        )

    # ---------------------------------------------------------
    # CREATE CLOUDINARY IMAGE
    # ---------------------------------------------------------
    def create_variant_image(
        self,
        variant,
        product_name,
        variant_name,
        variant_index,
    ):
        import cloudinary.uploader

        background = self.random.choice(
            self.IMAGE_BACKGROUNDS
        )

        safe_product_name = escape(
            product_name
        )

        safe_variant_name = escape(
            variant_name
        )

        svg = f"""<?xml version="1.0" encoding="UTF-8"?>
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
            y="735"
            text-anchor="middle"
            font-family="Arial, Helvetica, sans-serif"
            font-size="22"
            fill="#6B7280"
        >
            Variant {variant_index}
        </text>
    </svg>
    """

        # ---------------------------------------------------------
        # CLOUDINARY PUBLIC ID
        # ---------------------------------------------------------
        #
        # This is NOT a fake image.
        #
        # The SVG content is uploaded directly to Cloudinary and
        # Cloudinary returns the real public_id.
        #
        # ---------------------------------------------------------

        public_id = (
            f"mock-products/"
            f"{variant.product_id}/"
            f"variant-{variant_index}"
        )

        upload_result = cloudinary.uploader.upload(
            svg.encode("utf-8"),
            public_id=public_id,
            resource_type="image",
            format="svg",
            overwrite=True,
        )

        cloudinary_public_id = upload_result.get(
            "public_id"
        )

        if not cloudinary_public_id:
            raise RuntimeError(
                "Cloudinary upload succeeded but no public_id "
                "was returned."
            )

        # ---------------------------------------------------------
        # CREATE ProductVariantImage
        # ---------------------------------------------------------
        #
        # IMPORTANT:
        #
        # ProductVariantImage.save() calls full_clean().
        #
        # Therefore the CloudinaryField must contain the string
        # public_id BEFORE image.save() is called.
        #
        # ---------------------------------------------------------

        image = ProductVariantImage(
            variant=variant,
            image=cloudinary_public_id,
            alt_text=(
                f"{product_name} - "
                f"{variant_name}"
            ),
            is_primary=True,
            display_order=1,
            is_active=True,
        )

        image.save()

        return image

    # ---------------------------------------------------------
    # STORE OPERATING HOURS
    # ---------------------------------------------------------

    def create_store_operating_hours(
        self,
        store,
    ):
        for weekday, hours in self.STORE_HOURS.items():
            opens_at, closes_at = hours

            if opens_at is None:
                defaults = {
                    "is_closed": True,
                    "opens_at": None,
                    "closes_at": None,
                    "pickup_available": False,
                    "notes": "Store closed on Sunday.",
                }
            else:
                defaults = {
                    "is_closed": False,
                    "opens_at": opens_at,
                    "closes_at": closes_at,
                    "pickup_available": True,
                    "notes": "Regular store operating hours.",
                }

            StoreOperatingHour.objects.update_or_create(
                store=store,
                weekday=weekday,
                defaults=defaults,
            )

    # ---------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------

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
        }
