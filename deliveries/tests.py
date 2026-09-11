"""
Regression tests for the DeliveryAssignment refactor.

The refactor changed the model contract from "one ACTIVE assignment
per delivery" to "one LIFETIME assignment per delivery":

    - DeliveryAssignment.status uses the AssignmentStatus enum
      (the old DeliveryAssignment.Status reference was removed).
    - The database enforces a single DeliveryAssignment row per
      delivery via the unique_delivery_assignment OneToOne/Unique
      constraint.
    - A cancelled assignment is reused (never duplicated); every
      other assignment state blocks new offers.

These tests pin that contract so future refactors cannot silently
reintroduce multi-row assignments or stale enum references.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.generics import ValidationError

from deliveries.dispatch.exceptions import InvalidOfferState
from deliveries.dispatch.offer import DeliveryOfferService
from deliveries.models import Delivery, DeliveryAssignment, DeliveryOffer
from order.models import Order, OrderFulfillment
from vendors.models import VendorProfile, VendorStore


class DeliveryAssignmentRegressionTests(TestCase):
    """Pin the one-lifetime-assignment invariant and status API."""

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        # --------------------------------------------------------
        # Users
        # --------------------------------------------------------

        cls.customer = user_model.objects.create_user(
            email="customer.assignment@example.com",
            password="test-password",
            first_name="Test",
            last_name="Customer",
            phone_number="08010000001",
            role=user_model.Roles.CUSTOMER,
        )

        cls.rider_a = user_model.objects.create_user(
            email="rider.a.assignment@example.com",
            password="test-password",
            first_name="Rider",
            last_name="Alpha",
            phone_number="08010000002",
            role=user_model.Roles.RIDER,
        )

        cls.rider_b = user_model.objects.create_user(
            email="rider.b.assignment@example.com",
            password="test-password",
            first_name="Rider",
            last_name="Bravo",
            phone_number="08010000003",
            role=user_model.Roles.RIDER,
        )

        # --------------------------------------------------------
        # Vendor + store
        # --------------------------------------------------------

        vendor_user = user_model.objects.create_user(
            email="vendor.assignment@example.com",
            password="test-password",
            first_name="Vendor",
            last_name="Owner",
            phone_number="08010000004",
            role=user_model.Roles.VENDOR,
        )

        cls.vendor = VendorProfile.objects.get(user=vendor_user)
        cls.vendor.company_name = "Assignment Test Vendor"
        cls.vendor.save()

        cls.store = VendorStore.objects.create(
            vendor=cls.vendor,
            name="Assignment Test Store",
            slug="assignment-test-store",
            address_line_1="1 Test Street",
            city="Ikeja",
            state="Lagos",
            latitude=Decimal("6.6018380"),
            longitude=Decimal("3.3514860"),
        )

        # --------------------------------------------------------
        # Order → fulfillment → delivery
        # --------------------------------------------------------

        cls.order = Order.objects.create(
            customer=cls.customer,
            order_number="ORD-ASSIGNMENT-TEST-001",
        )

        cls.fulfillment = OrderFulfillment.objects.create(
            order=cls.order,
            store=cls.store,
            store_name="Assignment Test Store",
            store_address_line_1="1 Test Street",
            store_city="Ikeja",
            store_state="Lagos",
            store_latitude=Decimal("6.6018380"),
            store_longitude=Decimal("3.3514860"),
        )

        cls.delivery = Delivery.objects.create(
            fulfillment=cls.fulfillment,
            customer=cls.customer,
            vendor=cls.vendor,
            pickup_store=cls.store,
            pickup_store_name="Assignment Test Store",
            delivery_type=Delivery.DeliveryType.INSTANT,
        )

        cls.other_delivery = cls._create_delivery(
            order_number="ORD-ASSIGNMENT-TEST-002",
        )
# ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    @classmethod
    def _create_delivery(cls, order_number):
        """Create an additional order/fulfillment/delivery chain."""
        user_model = get_user_model()

        customer = user_model.objects.create_user(
            email=f"customer.{order_number.lower()}@example.com",
            password="test-password",
            first_name="Test",
            last_name="Customer",
            phone_number=f"0802{order_number[-3:]}",
            role=user_model.Roles.CUSTOMER,
        )

        order = Order.objects.create(
            customer=customer,
            order_number=order_number,
        )

        fulfillment = OrderFulfillment.objects.create(
            order=order,
            store=cls.store,
            store_name="Assignment Test Store",
            store_address_line_1="1 Test Street",
            store_city="Ikeja",
            store_state="Lagos",
            store_latitude=Decimal("6.6018380"),
            store_longitude=Decimal("3.3514860"),
        )

        return Delivery.objects.create(
            fulfillment=fulfillment,
            customer=customer,
            vendor=cls.vendor,
            pickup_store=cls.store,
            pickup_store_name="Assignment Test Store",
            delivery_type=Delivery.DeliveryType.INSTANT,
        )

    @classmethod
    def _restart_delivery(cls, delivery):
        """Explicit administrative restart into WAITING_FOR_RIDER."""
        delivery.status = Delivery.DeliveryStatus.WAITING_FOR_RIDER
        delivery.waiting_for_rider_at = timezone.now()
        delivery.save()
        return delivery

    # ------------------------------------------------------------
    # One-lifetime-assignment invariant
    # ------------------------------------------------------------

    def test_only_one_assignment_row_per_delivery(self):
        """A delivery can never have more than one assignment row."""
        DeliveryAssignment.objects.create(
            delivery=self.delivery,
            rider=self.rider_a,
            status=DeliveryAssignment.AssignmentStatus.ASSIGNED,
        )

        with self.assertRaises((IntegrityError, ValidationError)):
            with transaction.atomic():
                DeliveryAssignment.objects.create(
                    delivery=self.delivery,
                    rider=self.rider_b,
                    status=DeliveryAssignment.AssignmentStatus.ASSIGNED,
                )

        self.assertEqual(
            DeliveryAssignment.objects.filter(
                delivery_id=self.delivery.pk,
            ).count(),
            1,
            "A delivery must hold exactly one lifetime assignment.",
        )

    def test_cancelled_assignment_is_reused_not_duplicated(self):
        """A cancelled assignment is reused; no second row is created."""
        assignment = DeliveryAssignment.objects.create(
            delivery=self.delivery,
            rider=self.rider_a,
            status=DeliveryAssignment.AssignmentStatus.CANCELLED,
            cancelled_at=timezone.now(),
            is_active=False,
        )

        self._restart_delivery(self.delivery)

        assignment.status = DeliveryAssignment.AssignmentStatus.ASSIGNED
        assignment.is_active = True
        assignment.save()

        self.assertEqual(
            DeliveryAssignment.objects.filter(
                delivery_id=self.delivery.pk,
            ).count(),
            1,
            "Restarting a cancelled assignment must reuse the row.",
        )

        self.assertEqual(assignment.pk, self.delivery.assignment.pk)

    # ------------------------------------------------------------
    # Offer API status regression
    # ------------------------------------------------------------

    def test_completed_assignment_blocks_new_offer(self):
        """
        A COMPLETED assignment must reject new offers.

        Regression: the removed DeliveryAssignment.Status enum was
        referenced here; after the rename this path must raise
        InvalidOfferState, not AttributeError.
        """
        now = timezone.now()
        DeliveryAssignment.objects.create(
            delivery=self.other_delivery,
            rider=self.rider_a,
            status=DeliveryAssignment.AssignmentStatus.COMPLETED,
            accepted_at=now,
            completed_at=now,
            is_active=False,
        )

        with self.assertRaises(InvalidOfferState):
            DeliveryOfferService.create(
                delivery=self.other_delivery,
                rider=self.rider_b,
                radius=Decimal("5.00"),
                timeout=60,
            )

        self.assertFalse(
            DeliveryOffer.objects.filter(
                delivery_id=self.other_delivery.pk,
            ).exists(),
        )

    def test_cancelled_assignment_requires_restart_before_offer(self):
        """
        A CANCELLED assignment can only receive offers after the
        delivery is explicitly restarted into WAITING_FOR_RIDER.

        Regression: both the rejection and the acceptance branches
        navigate the renamed AssignmentStatus.CANCELLED member.
        """
        DeliveryAssignment.objects.create(
            delivery=self.other_delivery,
            rider=self.rider_a,
            status=DeliveryAssignment.AssignmentStatus.CANCELLED,
            cancelled_at=timezone.now(),
            is_active=False,
        )

        # Not restarted -> offer rejected (still exercises the enum).
        with self.assertRaises(InvalidOfferState):
            DeliveryOfferService.create(
                delivery=self.other_delivery,
                rider=self.rider_b,
                radius=Decimal("5.00"),
                timeout=60,
            )

        # Explicit restart -> offer allowed, no second assignment.
        self._restart_delivery(self.other_delivery)

        offer = DeliveryOfferService.create(
            delivery=self.other_delivery,
            rider=self.rider_b,
            radius=Decimal("5.00"),
            timeout=60,
        )

        self.assertIsNotNone(offer.pk)

        self.assertEqual(
            DeliveryAssignment.objects.filter(
                delivery_id=self.other_delivery.pk,
            ).count(),
            1,
            "A new offer must not create a second assignment row.",
        )
