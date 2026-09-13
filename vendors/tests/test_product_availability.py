"""
Tests for the product availability system.

The availability system determines whether a Product (or a
ProductVariant) can currently be presented as purchasable:

    Product.availability_status()
        Returns a dict with `is_available`, `checks`, and
        `reasons`. A product is available when:

            - is_active
            - is_published
            - is_in_stock (when inventory is tracked)
            - its store is active, verified, and accepting orders

    ProductVariant.can_be_purchased
        Returns whether the variant can be purchased now:

            - variant is_active
            - variant.is_available (database field)
            - parent product is available
            - variant is_in_stock (when inventory is tracked)
            - all option values and their options are active

Availability is enforced by the cart, checkout, and the
availability API at `vendors/products/availability/`.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from vendors.models import (
    Product,
    ProductCategory,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
    VendorProfile,
    VendorStore,
)


class ProductAvailabilityTestMixin:
    """Shared setup for building vendor/store/category/products."""

    @classmethod
    def _create_vendor_and_store(cls):
        user_model = get_user_model()

        vendor_user = user_model.objects.create_user(
            email="availability.vendor@example.com",
            password="test-password",
            first_name="Availability",
            last_name="Vendor",
            phone_number="08020000001",
            role=user_model.Roles.VENDOR,
        )

        vendor = VendorProfile.objects.get(user=vendor_user)
        vendor.company_name = "Availability Test Vendor"
        vendor.save()

        store = VendorStore.objects.create(
            vendor=vendor,
            name="Availability Test Store",
            slug="availability-test-store",
            address_line_1="1 Test Street",
            city="Ikeja",
            state="Lagos",
            phone="08020000002",
            latitude=Decimal("6.6018380"),
            longitude=Decimal("3.3514860"),
            is_active=True,
            is_verified=True,
            accepting_orders=True,
        )

        return vendor, store

    @classmethod
    def _create_category(cls, vendor):
        return ProductCategory.objects.create(
            name="Availability Test Category",
            slug="availability-test-category",
            description="Category used by availability tests.",
        )

    @classmethod
    def _create_product(cls, store, category=None, **kwargs):
        defaults = {
            "name": "Availability Test Product",
            "slug": "availability-test-product",
            "sku": "AVAILABILITY-SKU",
            "price": Decimal("1000.00"),
            "stock_quantity": 10,
            "track_inventory": True,
            "is_active": True,
            "is_published": True,
        }
        defaults.update(kwargs)
        return Product.objects.create(
            store=store,
            vendor=store.vendor,
            category=category,
            **defaults,
        )

    @classmethod
    def _create_variant(cls, product, **kwargs):
        defaults = {
            "name": "Default",
            "price": Decimal("1000.00"),
            "stock_quantity": 10,
            "track_inventory": True,
            "is_active": True,
            "is_available": True,
        }
        defaults.update(kwargs)
        return ProductVariant.objects.create(
            product=product,
            **defaults,
        )


class ProductAvailabilityStatusTests(ProductAvailabilityTestMixin, TestCase):
    """Tests for Product.availability_status()."""

    @classmethod
    def setUpTestData(cls):
        cls.vendor, cls.store = cls._create_vendor_and_store()
        cls.category = cls._create_category(cls.vendor)
        cls.product = cls._create_product(
            cls.store,
            cls.category,
        )

    def test_healthy_product_is_available(self):
        status = self.product.availability_status()

        self.assertTrue(status["is_available"])
        self.assertEqual(status["reasons"], [])
        self.assertTrue(status["checks"]["is_active"])
        self.assertTrue(status["checks"]["is_published"])
        self.assertTrue(status["checks"]["is_in_stock"])
        self.assertTrue(status["checks"]["store_is_active"])
        self.assertTrue(status["checks"]["store_is_verified"])
        self.assertTrue(status["checks"]["store_accepting_orders"])

    def test_inactive_product_is_unavailable(self):
        product = self._create_product(
            self.store,
            self.category,
            name="Inactive Product",
            slug="inactive-product",
            sku="AVAILABILITY-SKU-2",
            is_active=False,
        )

        status = product.availability_status()

        self.assertFalse(status["is_available"])
        self.assertIn("Product is inactive.", status["reasons"])

    def test_unpublished_product_is_unavailable(self):
        product = self._create_product(
            self.store,
            self.category,
            name="Unpublished Product",
            slug="unpublished-product",
            sku="AVAILABILITY-SKU-3",
            is_published=False,
        )

        status = product.availability_status()

        self.assertFalse(status["is_available"])
        self.assertIn("Product is not published.", status["reasons"])

    def test_out_of_stock_product_is_unavailable(self):
        product = self._create_product(
            self.store,
            self.category,
            name="Out of Stock Product",
            slug="out-of-stock-product",
            sku="AVAILABILITY-SKU-4",
            stock_quantity=0,
        )

        status = product.availability_status()

        self.assertFalse(status["is_available"])
        self.assertIn("Product is out of stock.", status["reasons"])
    
    def test_product_without_inventory_tracking_is_always_in_stock(self):
        product = self._create_product(
            self.store,
            self.category,
            name="No Tracking Product",
            slug="no-tracking-product",
            sku="AVAILABILITY-SKU-5",
            stock_quantity=0,
            track_inventory=False,
        )

        self.assertTrue(product.is_in_stock)
        self.assertTrue(
            product.availability_status()["checks"]["is_in_stock"]
        )
        self.assertTrue(product.is_available)

    def test_inactive_store_makes_product_unavailable(self):
        self.store.is_active = False
        self.store.save(
            update_fields=["is_active"],
        )

        try:
            status = self.product.availability_status()
            self.assertFalse(status["is_available"])
            self.assertIn("Store is inactive.", status["reasons"])
        finally:
            self.store.is_active = True
            self.store.save(
                update_fields=["is_active"],
            )

    def test_unverified_store_makes_product_unavailable(self):
        self.store.is_verified = False
        self.store.save(
            update_fields=["is_verified"],
        )

        try:
            status = self.product.availability_status()
            self.assertFalse(status["is_available"])
            self.assertIn("Store is not verified.", status["reasons"])
        finally:
            self.store.is_verified = True
            self.store.save(
                update_fields=["is_verified"],
            )

    def test_store_not_accepting_orders_makes_product_unavailable(self):
        self.store.accepting_orders = False
        self.store.save(
            update_fields=["accepting_orders"],
        )

        try:
            status = self.product.availability_status()
            self.assertFalse(status["is_available"])
            self.assertIn(
                "Store is not accepting orders.",
                status["reasons"],
            )
        finally:
            self.store.accepting_orders = True
            self.store.save(
                update_fields=["accepting_orders"],
            )

    def test_is_available_property_matches_status(self):
        self.assertEqual(
            self.product.is_available,
            self.product.availability_status()["is_available"],
        )


class ProductVariantPurchasableTests(ProductAvailabilityTestMixin, TestCase):
    """Tests for ProductVariant.can_be_purchased."""

    @classmethod
    def setUpTestData(cls):
        cls.vendor, cls.store = cls._create_vendor_and_store()
        cls.category = cls._create_category(cls.vendor)

        cls.product = cls._create_product(
            cls.store,
            cls.category,
        )

        cls.variant = cls._create_variant(
            cls.product,
        )

    def test_healthy_variant_can_be_purchased(self):
        self.assertTrue(self.variant.can_be_purchased)

    def test_inactive_variant_cannot_be_purchased(self):
        variant = self._create_variant(
            self.product,
            name="Inactive Variant",
            is_active=False,
        )

        self.assertFalse(variant.can_be_purchased)

    def test_unavailable_variant_cannot_be_purchased(self):
        variant = self._create_variant(
            self.product,
            name="Unavailable Variant",
            is_available=False,
        )

        self.assertFalse(variant.can_be_purchased)

    def test_out_of_stock_variant_cannot_be_purchased(self):
        variant = self._create_variant(
            self.product,
            name="Out of Stock Variant",
            stock_quantity=0,
        )

        self.assertFalse(variant.can_be_purchased)

    def test_variant_without_inventory_tracking_can_be_purchased(self):
        variant = self._create_variant(
            self.product,
            name="No Tracking Variant",
            stock_quantity=0,
            track_inventory=False,
        )

        self.assertTrue(variant.is_in_stock)
        self.assertTrue(variant.can_be_purchased)

    def test_unavailable_product_blocks_variant_purchase(self):
        product = self._create_product(
            self.store,
            self.category,
            name="Inactive Parent Product",
            slug="inactive-parent-product",
            sku="AVAILABILITY-SKU-6",
            is_active=False,
        )

        variant = self._create_variant(
            product,
            name="Orphan Available Variant",
        )

        self.assertFalse(variant.can_be_purchased)

    def test_inactive_option_value_blocks_variant_purchase(self):
        option = ProductOption.objects.create(
            product=self.product,
            name="Size",
            slug="size",
        )

        active_value = ProductOptionValue.objects.create(
            option=option,
            name="Large",
            slug="large",
            sort_order=1,
            is_active=True,
        )

        inactive_value = ProductOptionValue.objects.create(
            option=option,
            name="Extra Large",
            slug="extra-large",
            sort_order=2,
            is_active=False,
        )

        variant = self._create_variant(
            self.product,
            name="Option Variant",
        )
        variant.option_values.add(
            active_value
        )

        self.assertTrue(variant.can_be_purchased)

        variant.option_values.add(
            inactive_value
        )

        self.assertFalse(variant.can_be_purchased)


class ProductAvailabilityThroughCartTests(
    ProductAvailabilityTestMixin,
    TestCase,
):
    """
    Verify that the catalog availability gates stay aligned
    with what the cart can actually accept. Products and
    variants must be unavailable through the same checks
    that the cart and checkout enforce.
    """

    @classmethod
    def setUpTestData(cls):
        cls.vendor, cls.store = cls._create_vendor_and_store()
        cls.category = cls._create_category(cls.vendor)

        cls.product = cls._create_product(
            cls.store,
            cls.category,
        )

        cls.variant = cls._create_variant(
            cls.product,
        )

    def test_available_product_passes_cart_gate(self):
        self.assertTrue(self.product.is_available)
        self.assertTrue(self.variant.can_be_purchased)

    def test_unpublished_product_has_cart_gate_blocked(self):
        product = self._create_product(
            self.store,
            self.category,
            name="Hidden Product",
            slug="hidden-product",
            sku="AVAILABILITY-SKU-7",
            is_published=False,
        )

        self.assertFalse(product.is_available)

    def test_out_of_stock_product_has_cart_gate_blocked(self):
        product = self._create_product(
            self.store,
            self.category,
            name="Depleted Product",
            slug="depleted-product",
            sku="AVAILABILITY-SKU-8",
            stock_quantity=0,
        )

        self.assertFalse(product.is_available)

    def test_unavailable_variant_has_cart_gate_blocked(self):
        variant = self._create_variant(
            self.product,
            name="Sold Out Variant",
            stock_quantity=0,
        )

        self.assertFalse(variant.can_be_purchased)