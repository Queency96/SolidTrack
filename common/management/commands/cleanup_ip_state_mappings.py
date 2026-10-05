"""
Delete stale IPStateMapping rows.

Mappings with no new evidence in MAPPING_TTL_DAYS are removed.
Handles carrier IP reassignment, where the same IP gets handed
to a new customer in a different state.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from common.models import (
    MAPPING_TTL_DAYS,
    IPStateMapping,
)


class Command(BaseCommand):

    help = (
        "Delete IPStateMapping rows with no recent evidence."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be deleted without deleting.",
        )

    def handle(self, *args, **options):

        cutoff = timezone.now() - timedelta(days=MAPPING_TTL_DAYS)

        queryset = IPStateMapping.objects.filter(
            last_seen_at__lt=cutoff,
        )

        count = queryset.count()

        if options["dry_run"]:
            self.stdout.write(
                f"[dry-run] Would delete {count} stale mappings."
            )
            return

        queryset.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {count} stale IPStateMapping rows."
            )
        )