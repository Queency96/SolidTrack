"""
Admin registrations for the common app.

Currently hosts:

    IPStateMapping — the learned IP -> Nigerian state table
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from common.models import (
    MAPPING_TTL_DAYS,
    MIN_CONFIDENCE,
    IPStateMapping,
)


@admin.register(IPStateMapping)
class IPStateMappingAdmin(admin.ModelAdmin):
    """
    Read-only-ish admin for the learned IP -> state table.

    Rows are written automatically by the customer browse flow
    when a phone-verified user explicitly picks a state via
    ?state=. Admins inspect and delete; they do not create or
    edit rows, because the model's trust gate depends on real
    user votes.

    Trust rule
    ----------
    A mapping becomes trusted once MIN_CONFIDENCE distinct,
    phone-verified users have voted for the same state on the
    same IP. Until then, the browse flow falls through to the
    external IP providers.

    Expiry
    ------
    Mappings with no new evidence in MAPPING_TTL_DAYS days
    are removed by the daily cleanup task.
    """

    list_display = (
        "ip",
        "state_code",
        "confidence_display",
        "trusted_badge",
        "distinct_voters_display",
        "age_display",
        "last_seen_at",
    )

    list_filter = (
        "state_code",
        "last_seen_at",
    )

    search_fields = (
        "ip",
        "state_code",
    )

    ordering = ("-last_seen_at",)

    list_per_page = 50

    readonly_fields = (
        "id",
        "ip",
        "state_code",
        "confidence",
        "trusted_badge",
        "distinct_voters_display",
        "evidence",
        "first_seen_at",
        "last_seen_at",
        "age_display",
    )

    fieldsets = (
        (
            "Mapping",
            {
                "fields": (
                    "id",
                    "ip",
                    "state_code",
                    "confidence",
                    "trusted_badge",
                ),
            },
        ),
        (
            "Evidence",
            {
                "fields": (
                    "evidence",
                    "distinct_voters_display",
                ),
                "description": (
                    f"A mapping becomes trusted once "
                    f"<strong>{MIN_CONFIDENCE}</strong> "
                    "distinct phone-verified users agree on "
                    "the same state for this IP. Rows with no "
                    f"new evidence in "
                    f"<strong>{MAPPING_TTL_DAYS}</strong> "
                    "days are removed by the daily cleanup "
                    "task."
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "first_seen_at",
                    "last_seen_at",
                    "age_display",
                ),
            },
        ),
    )

    actions = (
        "clear_selected_mappings",
    )

    # ------------------------------------------------------
    # Permissions
    # ------------------------------------------------------

    def has_add_permission(self, request):
        # Rows are learned from real user votes.
        return False

    def has_change_permission(self, request, obj=None):
        # Read-only inspection only.
        return False

    def has_delete_permission(self, request, obj=None):
        # Deletion is allowed — via the custom action or
        # individual delete.
        return True

    # ------------------------------------------------------
    # Column displays
    # ------------------------------------------------------

    @admin.display(
        description="Confidence",
        ordering="confidence",
    )
    def confidence_display(self, obj):
        return f"{obj.confidence} / {MIN_CONFIDENCE}"

    # ------------------------------------------------------

    @admin.display(description="Trusted")
    def trusted_badge(self, obj):

        if obj.confidence >= MIN_CONFIDENCE:
            return format_html(
                '<span style="color: #0a7d2e; '
                'font-weight: bold;">Yes</span>'
            )

        return format_html(
            '<span style="color: #888;">No</span>'
        )

    # ------------------------------------------------------

    @admin.display(description="Distinct voters")
    def distinct_voters_display(self, obj):
        """
        Total distinct user UUIDs recorded across every state
        candidate for this IP.
        """

        evidence = obj.evidence or {}

        total = 0

        for user_ids in evidence.values():
            total += len(set(str(uid) for uid in user_ids))

        return total

    # ------------------------------------------------------

    @admin.display(description="Age")
    def age_display(self, obj):

        if obj.last_seen_at is None:
            return "—"

        delta = timezone.now() - obj.last_seen_at
        days = delta.days

        if days <= 0:
            return "Today"

        if days == 1:
            return "Yesterday"

        if days < MAPPING_TTL_DAYS:
            return f"{days}d ago"

        return format_html(
            '<span style="color: #c0392b; '
            'font-weight: bold;">'
            "{}d ago (expired)</span>",
            days,
        )

    # ------------------------------------------------------
    # Actions
    # ------------------------------------------------------

    @admin.action(
        description=(
            "Clear selected IP -> state mappings "
            "(forces re-learning)"
        )
    )
    def clear_selected_mappings(self, request, queryset):

        count = queryset.count()

        queryset.delete()

        self.message_user(
            request,
            f"Cleared {count} IP state mapping(s). "
            "The browse flow will re-learn from future "
            "user votes.",
        )