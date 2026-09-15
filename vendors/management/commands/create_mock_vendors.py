import random
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from vendors.models import VendorProfile, VendorStore


User = get_user_model()


class Command(BaseCommand):
    """
    Create mock vendor accounts and vendor stores.

    Each vendor gets 5 stores by default.

    IMPORTANT:
        Each store belonging to the same vendor is created
        in a different location.

    Example:

        Vendor 1
        ├── Store 1 → Lagos
        ├── Store 2 → Abuja
        ├── Store 3 → Port Harcourt
        ├── Store 4 → Ibadan
        └── Store 5 → Enugu

    Commands:

        python manage.py create_mock_vendors

        python manage.py create_mock_vendors --vendor-count 20

        python manage.py create_mock_vendors --stores-per-vendor 5

        python manage.py create_mock_vendors --overwrite
    """

    help = "Create mock vendors with 5 stores in different locations."

    # ==========================================================
    # LOCATIONS
    # ==========================================================

    LOCATIONS = [
        {
            "city": "Lagos",
            "state": "Lagos",
            "latitude": Decimal("6.5244000"),
            "longitude": Decimal("3.3792000"),
            "postal_code": "100001",
        },
        {
            "city": "Ikeja",
            "state": "Lagos",
            "latitude": Decimal("6.6018000"),
            "longitude": Decimal("3.3515000"),
            "postal_code": "100212",
        },
        {
            "city": "Lekki",
            "state": "Lagos",
            "latitude": Decimal("6.4698000"),
            "longitude": Decimal("3.5852000"),
            "postal_code": "105102",
        },
        {
            "city": "Victoria Island",
            "state": "Lagos",
            "latitude": Decimal("6.4281000"),
            "longitude": Decimal("3.4219000"),
            "postal_code": "101241",
        },
        {
            "city": "Yaba",
            "state": "Lagos",
            "latitude": Decimal("6.5158000"),
            "longitude": Decimal("3.3898000"),
            "postal_code": "101212",
        },
        {
            "city": "Surulere",
            "state": "Lagos",
            "latitude": Decimal("6.4969000"),
            "longitude": Decimal("3.3596000"),
            "postal_code": "101283",
        },
        {
            "city": "Abuja",
            "state": "FCT",
            "latitude": Decimal("9.0765000"),
            "longitude": Decimal("7.3986000"),
            "postal_code": "900001",
        },
        {
            "city": "Port Harcourt",
            "state": "Rivers",
            "latitude": Decimal("4.8156000"),
            "longitude": Decimal("7.0498000"),
            "postal_code": "500001",
        },
        {
            "city": "Benin City",
            "state": "Edo",
            "latitude": Decimal("6.3350000"),
            "longitude": Decimal("5.6037000"),
            "postal_code": "300001",
        },
        {
            "city": "Ibadan",
            "state": "Oyo",
            "latitude": Decimal("7.3775000"),
            "longitude": Decimal("3.9470000"),
            "postal_code": "200001",
        },
        {
            "city": "Kano",
            "state": "Kano",
            "latitude": Decimal("12.0022000"),
            "longitude": Decimal("8.5920000"),
            "postal_code": "700001",
        },
        {
            "city": "Enugu",
            "state": "Enugu",
            "latitude": Decimal("6.4584000"),
            "longitude": Decimal("7.5464000"),
            "postal_code": "400001",
        },
        {
            "city": "Asaba",
            "state": "Delta",
            "latitude": Decimal("6.1944000"),
            "longitude": Decimal("6.7316000"),
            "postal_code": "320001",
        },
        {
            "city": "Warri",
            "state": "Delta",
            "latitude": Decimal("5.5167000"),
            "longitude": Decimal("5.7500000"),
            "postal_code": "332001",
        },
        {
            "city": "Abeokuta",
            "state": "Ogun",
            "latitude": Decimal("7.1475000"),
            "longitude": Decimal("3.3619000"),
            "postal_code": "110001",
        },
        {
            "city": "Ilorin",
            "state": "Kwara",
            "latitude": Decimal("8.4966000"),
            "longitude": Decimal("4.5421000"),
            "postal_code": "240001",
        },
        {
            "city": "Akure",
            "state": "Ondo",
            "latitude": Decimal("7.2571000"),
            "longitude": Decimal("5.2058000"),
            "postal_code": "340001",
        },
        {
            "city": "Jos",
            "state": "Plateau",
            "latitude": Decimal("9.8965000"),
            "longitude": Decimal("8.8583000"),
            "postal_code": "930001",
        },
        {
            "city": "Kaduna",
            "state": "Kaduna",
            "latitude": Decimal("10.5105000"),
            "longitude": Decimal("7.4165000"),
            "postal_code": "800001",
        },
        {
            "city": "Calabar",
            "state": "Cross River",
            "latitude": Decimal("4.9757000"),
            "longitude": Decimal("8.3417000"),
            "postal_code": "540001",
        },
    ]

    # ==========================================================
    # COMPANY DATA
    # ==========================================================

    COMPANY_PREFIXES = [
        "Prime",
        "Royal",
        "Global",
        "Smart",
        "Elite",
        "Metro",
        "Green",
        "Swift",
        "Urban",
        "Golden",
        "Capital",
        "First",
        "Trusted",
        "Mega",
        "Reliable",
    ]

    COMPANY_TYPES = [
        "Distributors",
        "Supplies",
        "Enterprises",
        "Trading",
        "Merchants",
        "Wholesale",
        "Ventures",
        "Commerce",
        "Stores",
        "Logistics",
    ]

    STREET_NAMES = [
        "Commerce",
        "Market",
        "Industrial",
        "Business",
        "Warehouse",
        "Trade",
        "Unity",
        "Airport",
        "Station",
        "Central",
    ]

    NIGERIAN_PHONE_PREFIXES = [
        "0803",
        "0805",
        "0806",
        "0807",
        "0809",
        "0810",
        "0811",
        "0812",
        "0813",
        "0814",
        "0815",
        "0816",
        "0817",
        "0818",
        "0819",
        "0901",
        "0902",
        "0903",
        "0904",
        "0905",
        "0906",
        "0907",
        "0908",
        "0909",
        "0910",
        "0911",
        "0912",
        "0913",
        "0914",
        "0915",
        "0916",
        "0917",
        "0918",
        "0919",
    ]

    # ==========================================================
    # COMMAND ARGUMENTS
    # ==========================================================

    def add_arguments(self, parser):

        parser.add_argument(
            "--vendor-count",
            type=int,
            default=10,
            help="Number of vendors to create. Default: 10.",
        )

        parser.add_argument(
            "--stores-per-vendor",
            type=int,
            default=5,
            help="Number of stores per vendor. Default: 5.",
        )

        parser.add_argument(
            "--overwrite",
            action="store_true",
            help=(
                "Delete previously generated mock vendors "
                "before creating new ones."
            ),
        )

    # ==========================================================
    # HANDLE
    # ==========================================================

    def handle(self, *args, **options):

        vendor_count = options["vendor_count"]
        stores_per_vendor = options["stores_per_vendor"]
        overwrite = options["overwrite"]

        if vendor_count < 1:

            self.stdout.write(
                self.style.ERROR(
                    "vendor-count must be at least 1."
                )
            )

            return

        if stores_per_vendor < 1:

            self.stdout.write(
                self.style.ERROR(
                    "stores-per-vendor must be at least 1."
                )
            )

            return

        # ------------------------------------------------------
        # We need enough different locations.
        # ------------------------------------------------------

        if stores_per_vendor > len(self.LOCATIONS):

            self.stdout.write(
                self.style.ERROR(
                    f"You requested {stores_per_vendor} stores "
                    f"per vendor, but only "
                    f"{len(self.LOCATIONS)} different locations "
                    f"are configured."
                )
            )

            return

        # ------------------------------------------------------
        # Overwrite
        # ------------------------------------------------------

        if overwrite:

            self.stdout.write(
                self.style.WARNING(
                    "Deleting previously generated "
                    "mock vendors..."
                )
            )

            self._delete_existing_vendors()

            self.stdout.write("")

        # ------------------------------------------------------
        # Header
        # ------------------------------------------------------

        self.stdout.write(
            self.style.SUCCESS(
                f"Creating {vendor_count} mock vendor(s)..."
            )
        )

        self.stdout.write(
            f"Each vendor will have "
            f"{stores_per_vendor} stores."
        )

        self.stdout.write(
            "Each vendor's stores will be in "
            "different locations."
        )

        self.stdout.write("")

        vendors_created = 0
        vendors_skipped = 0
        stores_created = 0

        # ======================================================
        # CREATE VENDORS
        # ======================================================

        for vendor_number in range(
            1,
            vendor_count + 1,
        ):

            try:

                with transaction.atomic():

                    # ------------------------------------------
                    # User
                    # ------------------------------------------

                    email = (
                        self._generate_unique_vendor_email(
                            vendor_number
                        )
                    )

                    phone_number = (
                        self._generate_unique_phone()
                    )

                    company_name = (
                        self._generate_unique_company_name()
                    )

                    user = User.objects.create_user(
                        email=email,
                        phone_number=phone_number,
                        password="password123",
                        first_name=f"Vendor{vendor_number}",
                        last_name="Admin",
                    )

                    # ------------------------------------------
                    # Vendor profile
                    # ------------------------------------------

                    vendor_profile = (
                        VendorProfile.objects.create(
                            user=user,
                            company_name=company_name,
                            business_registration_number=(
                                self._generate_business_number()
                            ),
                            tax_number=(
                                self._generate_tax_number()
                            ),
                            verification_status=(
                                VendorProfile
                                .VerificationStatus
                                .APPROVED
                            ),
                        )
                    )

                    # ------------------------------------------
                    # FIVE DIFFERENT LOCATIONS
                    # ------------------------------------------

                    locations = (
                        self._get_unique_locations(
                            stores_per_vendor
                        )
                    )

                    # ------------------------------------------
                    # Stores
                    # ------------------------------------------

                    vendor_stores = []

                    for store_number, location in enumerate(
                        locations,
                        start=1,
                    ):

                        store = (
                            self._create_store(
                                vendor_profile=vendor_profile,
                                company_name=company_name,
                                store_number=store_number,
                                location=location,
                                total_stores=stores_per_vendor,
                            )
                        )

                        vendor_stores.append(store)

                    # ------------------------------------------
                    # Counters
                    # ------------------------------------------

                    vendors_created += 1

                    stores_created += len(
                        vendor_stores
                    )

                    # ------------------------------------------
                    # Output
                    # ------------------------------------------

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Vendor {vendor_number} created"
                        )
                    )

                    self.stdout.write(
                        f"  Company: {company_name}"
                    )

                    self.stdout.write(
                        f"  Email:   {email}"
                    )

                    self.stdout.write(
                        f"  Phone:   {phone_number}"
                    )

                    self.stdout.write(
                        f"  Stores:  "
                        f"{len(vendor_stores)}"
                    )

                    for store in vendor_stores:

                        self.stdout.write(
                            f"    • {store.name}"
                        )

                        self.stdout.write(
                            f"      Location: "
                            f"{store.city}, "
                            f"{store.state}"
                        )

                        self.stdout.write(
                            f"      GPS: "
                            f"{store.latitude}, "
                            f"{store.longitude}"
                        )

                    self.stdout.write("")

            except Exception as exc:

                vendors_skipped += 1

                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to create Vendor "
                        f"{vendor_number}: {exc}"
                    )
                )

        # ======================================================
        # SUMMARY
        # ======================================================

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 60)

        self.stdout.write(
            f"Vendors created: {vendors_created}"
        )

        self.stdout.write(
            f"Vendors skipped: {vendors_skipped}"
        )

        self.stdout.write(
            f"Stores created:  {stores_created}"
        )

        # ======================================================
        # LOGIN
        # ======================================================

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("LOGIN CREDENTIALS")
        self.stdout.write("=" * 60)

        self.stdout.write(
            "Email:    vendor1@soliddistributor.com"
        )

        self.stdout.write(
            "Password: password123"
        )

        self.stdout.write("")

    # ==========================================================
    # GET UNIQUE LOCATIONS
    # ==========================================================

    def _get_unique_locations(
        self,
        number_of_stores,
    ):
        """
        Select distinct locations for ONE vendor.

        Example for 5 stores:

            Lagos
            Abuja
            Port Harcourt
            Ibadan
            Enugu

        The locations are sampled without replacement,
        therefore the same vendor can never receive two
        stores in the same configured location.
        """

        return random.sample(
            self.LOCATIONS,
            number_of_stores,
        )

    # ==========================================================
    # CREATE STORE
    # ==========================================================

    def _create_store(
        self,
        vendor_profile,
        company_name,
        store_number,
        location,
        total_stores,
    ):

        # ------------------------------------------------------
        # Store name
        # ------------------------------------------------------

        store_name = (
            self._generate_store_name(
                company_name=company_name,
                location=location,
                store_number=store_number,
                total_stores=total_stores,
            )
        )

        # ------------------------------------------------------
        # Slug
        # ------------------------------------------------------

        slug = (
            self._generate_unique_store_slug(
                vendor=vendor_profile,
                store_name=store_name,
            )
        )

        # ------------------------------------------------------
        # Coordinates
        # ------------------------------------------------------

        latitude, longitude = (
            self._randomize_coordinates(
                location["latitude"],
                location["longitude"],
            )
        )

        # ------------------------------------------------------
        # Address
        # ------------------------------------------------------

        house_number = random.randint(
            1,
            150,
        )

        street = random.choice(
            self.STREET_NAMES
        )

        address_line_1 = (
            f"{house_number} "
            f"{street} Street"
        )

        # ------------------------------------------------------
        # Phone
        # ------------------------------------------------------

        phone = (
            self._generate_unique_phone()
        )

        # ------------------------------------------------------
        # Email
        # ------------------------------------------------------

        email = (
            f"{slug}@soliddistributor.com"
        )

        # ------------------------------------------------------
        # Create store
        # ------------------------------------------------------

        return VendorStore.objects.create(

            vendor=vendor_profile,

            name=store_name,

            slug=slug,

            description=(
                f"{store_name} is a branch of "
                f"{company_name}, serving customers "
                f"and preparing orders for delivery."
            ),

            phone=phone,

            email=email,

            address_line_1=address_line_1,

            address_line_2="",

            city=location["city"],

            state=location["state"],

            country="Nigeria",

            postal_code=location["postal_code"],

            latitude=latitude,

            longitude=longitude,

            is_active=True,

            is_verified=True,

            accepting_orders=True,

            accepting_pickups=True,

            pickup_instructions=(
                "Rider should report to the store "
                "pickup desk and present the delivery "
                "assignment before collecting the package."
            ),

            preparation_time_minutes=random.choice(
                [
                    15,
                    20,
                    30,
                    45,
                    60,
                ]
            ),

            # Only the first store is default.
            is_default=(
                store_number == 1
            ),
        )

    # ==========================================================
    # STORE NAME
    # ==========================================================

    def _generate_store_name(
        self,
        company_name,
        location,
        store_number,
        total_stores,
    ):

        return (
            f"{company_name} - "
            f"{location['city']} Branch"
        )

    # ==========================================================
    # COMPANY NAME
    # ==========================================================

    def _generate_unique_company_name(self):

        max_attempts = 100

        for _ in range(max_attempts):

            company_name = (
                f"{random.choice(self.COMPANY_PREFIXES)} "
                f"{random.choice(self.COMPANY_TYPES)}"
            )

            if not VendorProfile.objects.filter(
                company_name=company_name
            ).exists():

                return company_name

        return (
            "Solid Distributor "
            f"{random.randint(10000, 99999)}"
        )

    # ==========================================================
    # EMAIL
    # ==========================================================

    def _generate_unique_vendor_email(
        self,
        vendor_number,
    ):

        base_email = (
            f"vendor{vendor_number}"
            "@soliddistributor.com"
        )

        if not User.objects.filter(
            email=base_email
        ).exists():

            return base_email

        counter = 2

        while True:

            email = (
                f"vendor{vendor_number}_{counter}"
                "@soliddistributor.com"
            )

            if not User.objects.filter(
                email=email
            ).exists():

                return email

            counter += 1

    # ==========================================================
    # PHONE
    # ==========================================================

    def _generate_unique_phone(self):

        max_attempts = 1000

        for _ in range(max_attempts):

            prefix = random.choice(
                self.NIGERIAN_PHONE_PREFIXES
            )

            subscriber_number = "".join(
                str(random.randint(0, 9))
                for _ in range(7)
            )

            phone = (
                f"{prefix}{subscriber_number}"
            )

            # User.phone_number is unique.
            if User.objects.filter(
                phone_number=phone
            ).exists():

                continue

            return phone

        raise RuntimeError(
            "Unable to generate a unique "
            "Nigerian phone number."
        )

    # ==========================================================
    # STORE SLUG
    # ==========================================================

    def _generate_unique_store_slug(
        self,
        vendor,
        store_name,
    ):

        base_slug = slugify(
            store_name
        )

        slug = base_slug
        counter = 2

        while VendorStore.objects.filter(
            vendor=vendor,
            slug=slug,
        ).exists():

            slug = (
                f"{base_slug}-{counter}"
            )

            counter += 1

        return slug

    # ==========================================================
    # BUSINESS REGISTRATION
    # ==========================================================

    def _generate_business_number(self):

        return (
            f"RC"
            f"{random.randint(1000000, 9999999)}"
        )

    # ==========================================================
    # TAX NUMBER
    # ==========================================================

    def _generate_tax_number(self):

        return (
            f"NG-TIN-"
            f"{random.randint(100000000, 999999999)}"
        )

    # ==========================================================
    # COORDINATES
    # ==========================================================

    def _randomize_coordinates(
        self,
        latitude,
        longitude,
    ):
        """
        Add a small coordinate variation around the
        configured location.

        This means two different vendors can have
        stores in the same city while still having
        slightly different GPS pickup points.

        However, stores belonging to the SAME vendor
        are always assigned different base locations.
        """

        latitude_offset = Decimal(
            str(
                round(
                    random.uniform(
                        -0.015,
                        0.015,
                    ),
                    7,
                )
            )
        )

        longitude_offset = Decimal(
            str(
                round(
                    random.uniform(
                        -0.015,
                        0.015,
                    ),
                    7,
                )
            )
        )

        latitude = (
            latitude + latitude_offset
        )

        longitude = (
            longitude + longitude_offset
        )

        latitude = max(
            Decimal("-90"),
            min(
                Decimal("90"),
                latitude,
            ),
        )

        longitude = max(
            Decimal("-180"),
            min(
                Decimal("180"),
                longitude,
            ),
        )

        return (
            latitude,
            longitude,
        )

    # ==========================================================
    # DELETE EXISTING MOCK VENDORS
    # ==========================================================

    def _delete_existing_vendors(self):

        mock_users = User.objects.filter(
            email__iendswith="@soliddistributor.com"
        )

        count = mock_users.count()

        if count:
            mock_users.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {count} existing mock "
                f"vendor user(s)."
            )
        )
