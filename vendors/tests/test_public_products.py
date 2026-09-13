from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import User
from vendors.models import (
    Product,
    ProductCategory,
    VendorProfile,
    VendorStore,
)


class PublicProductListViewTest(TestCase):
    """Test the public product listing API."""

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="vendor@example.com",
            password="testpass123",
            first_name="Vendor",
            last_name="User",
        )

        self.vendor = VendorProfile.objects.create(
            user=self.user,
            company_name="Test Vendor",
        )

        self.category = ProductCategory.objects.create(
            name="Electronics",
            slug="electronics",
            is_active=True,
        )

        self.store = VendorStore.objects.create(
            vendor=self.vendor,
            name="Test Store",
            slug="test-store",
            address_line_1="123 Test St",
            city="Lagos",
            state="Lagos",
            country="Nigeria",
            latitude=6.5244,
            longitude=3.3792,
            is_active=True,
            is_verified=True,
            accepting_orders=True,
        )

        self.product = Product.objects.create(
            vendor=self.vendor,
            store=self.store,
            category=self.category,
            name="Test Product",
            slug="test-product",
            sku="TEST-001",
            short_description="A test product",
            description="Full description",
            price=100.00,
            stock_quantity=10,
            is_active=True,
            is_published=True,
        )

    def test_filter_by_in_stock(self):
        response = self.client.get("/products/", {"in_stock": "true"})
        self.assertEqual(len(response.data), 1)
        out_of_stock = Product.objects.create(
            vendor=self.vendor,
            store=self.store,
            category=self.category,
            name="Out of Stock Product",
            slug="out-of-stock",
            sku="TEST-003",
            price=50.00,
            stock_quantity=0,
            is_active=True,
            is_published=True,
        )
        self.assertTrue(out_of_stock.pk)
        response = self.client.get("/products/", {"in_stock": "true"})
        for item in response.data:
            self.assertTrue(item["is_in_stock"])

    def test_search_by_name(self):
        response = self.client.get("/products/", {"search": "Test Product"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_detail_view_returns_product(self):
        response = self.client.get(f"/products/{self.product.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["name"], "Test Product")
        self.assertEqual(data["slug"], "test-product")
        self.assertIn("images", data)
        self.assertIn("variants", data)

    def test_detail_view_404_for_unpublished(self):
        response = self.client.get(f"/products/{self.unpublished.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PublicProductSerializerTest(TestCase):
    """Test the public product serializers."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="vendor2@example.com",
            password="testpass123",
            first_name="Vendor",
            last_name="User",
        )

        self.vendor = VendorProfile.objects.create(
            user=self.user,
            company_name="Test Vendor Co",
        )

        self.category = ProductCategory.objects.create(
            name="Electronics",
            slug="electronics",
            is_active=True,
        )

        self.store = VendorStore.objects.create(
            vendor=self.vendor,
            name="Downtown Store",
            slug="downtown",
            address_line_1="123 Main St",
            city="Lagos",
            state="Lagos",
            country="Nigeria",
            latitude=6.5244,
            longitude=3.3792,
            is_active=True,
            is_verified=True,
            accepting_orders=True,
        )

        self.product = Product.objects.create(
            vendor=self.vendor,
            store=self.store,
            category=self.category,
            name="Smartphone",
            slug="smartphone",
            sku="PHONE-001",
            short_description="Latest model",
            price=50000.00,
            compare_at_price=60000.00,
            stock_quantity=25,
            is_active=True,
            is_published=True,
            is_featured=True,
        )

    def test_serializer_exposes_expected_fields(self):
        from vendors.serializers.product import PublicProductSerializer

        serializer = PublicProductSerializer(self.product)
        data = serializer.data

        for field in (
            "id",
            "name",
            "slug",
            "price",
            "category_name",
            "vendor_name",
            "store_name",
            "is_available",
            "is_in_stock",
            "primary_image",
        ):
            self.assertIn(field, data)

        self.assertEqual(data["category_name"], "Electronics")
        self.assertEqual(data["vendor_name"], "Test Vendor Co")
        self.assertEqual(data["store_name"], "Downtown Store")
        self.unpublished = Product.objects.create(
            vendor=self.vendor,
            store=self.store,
            category=self.category,
            name="Unpublished Product",
            slug="unpublished",
            sku="TEST-002",
            price=200.00,
            stock_quantity=5,
            is_active=True,
            is_published=False,
        )

    def test_list_returns_only_published_products(self):
        response = self.client.get("/products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], "test-product")

    def test_unpublished_products_hidden(self):
        response = self.client.get("/products/")
        slugs = [p["slug"] for p in response.data]
        self.assertNotIn("unpublished", slugs)

    def test_filter_by_category(self):
        response = self.client.get("/products/", {"category": "electronics"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_by_store(self):
        response = self.client.get("/products/", {"store": "test-store"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_by_featured(self):
        response = self.client.get("/products/", {"featured": "true"})
        self.assertEqual(len(response.data), 0)
        self.product.is_featured = True
        self.product.save()
        response = self.client.get("/products/", {"featured": "true"})
        self.assertEqual(len(response.data), 1)
