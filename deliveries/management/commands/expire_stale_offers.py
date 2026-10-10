"""
Manually expire stale delivery offers.

Useful when:
    - Celery beat has been down and offers are stuck.
    - You want to test the expiry path without waiting 60s.
    - You're running maintenance.

Usage:
    python manage.py expire_stale_offers --dry-run
    python manage.py expire_stale_offers
    python manage.py expire_stale_offers --batch-size 200
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from deliveries.dispatch.coordinator import DispatchCoordinator
from deliveries.models import DeliveryOffer


DEFAULT_BATCH_SIZE = 200


class Command(BaseCommand):

    help = (
        "Expire PENDING delivery offers whose expires_at has "
        "passed, and trigger redispatch."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be expired without expiring.",
        )

        parser.add_argument(
            "--batch-size",
            type=int,
            default=DEFAULT_BATCH_SIZE,
            help=(
                f"Maximum offers to process per run. "
                f"Default: {DEFAULT_BATCH_SIZE}."
            ),
        )

    def handle(self, *args, **options):

        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        now = timezone.now()

        offers = (
            DeliveryOffer.objects
            .filter(
                status=DeliveryOffer.Status.PENDING,
                expires_at__lte=now,
            )
            .select_related("delivery", "rider")
            .order_by("expires_at")[:batch_size]
        )

        total = offers.count()

        if total == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "No expired pending offers found."
                )
            )
            return

        if dry_run:
            self.stdout.write(
                f"[dry-run] Would expire {total} offers:"
            )

            for offer in offers:
                self.stdout.write(
                    f"  - {offer.pk} "
                    f"(delivery={offer.delivery_id}, "
                    f"rider={offer.rider_id}, "
                    f"expires_at={offer.expires_at.isoformat()})"
                )
            return

        expired = 0
        failed = 0

        for offer in offers:

            try:
                DispatchCoordinator.offer_expired(offer)
                expired += 1

            except Exception as exc:
                self.stderr.write(
                    f"Failed to expire {offer.pk}: {exc}"
                )
                failed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {expired} offers "
                f"({failed} failed)."
            )
        )