from django.db import models
import uuid
from common.constant import NIGERIA_STATE_CHOICES




class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True





# Minimum distinct verified users required before an IP -> state
# mapping is trusted and used in the lookup chain.
MIN_CONFIDENCE = 3

# Mappings with no new evidence in this many days are deleted by
# the cleanup job. Handles carrier IP reassignment.
MAPPING_TTL_DAYS = 90


class IPStateMapping(models.Model):
    """
    Aggregated IP -> Nigerian state mapping.

    PURPOSE
    -------
    Build a Nigeria-specific IP geolocation table from verified user
    signals, replacing reliance on generic providers that are unreliable
    for Nigerian networks.

    TRUST MODEL
    -----------
    A mapping is only trusted once MIN_CONFIDENCE distinct, phone-verified
    users have explicitly selected the same state via ?state= while on the
    same IP.

    Single-user overrides never promote a mapping. Contradicting votes
    never overwrite a mapping. Inactive mappings expire.

    The table learns from:
        • Explicit user state selection (?state=)
        • Only when the user is authenticated AND phone-verified

    The table never learns from:
        • IP-derived results (would train on our own predictions)
        • Anonymous users
        • Unverified users
        • Same-user repeat votes (deduplicated by user_id)
    """


    """
    Aggregated evidence for the state a given IP is likely in.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    ip = models.GenericIPAddressField(
        unique=True,
        db_index=True,
    )

    state_code = models.CharField(
        max_length=2,
        choices=NIGERIA_STATE_CHOICES,
        db_index=True,
    )

    # Distinct verified users whose explicit selection agreed
    # with `state_code`. This is the promotion gate.
    confidence = models.PositiveIntegerField(default=0)

    # Per-state distinct-user counts. Used to:
    #   • detect a challenger before promoting it
    #   • prevent the same user voting twice
    #
    # Shape:
    #   {
    #     "LA": ["<user_uuid>", "<user_uuid>"],
    #     "OG": ["<user_uuid>"],
    #   }
    #
    # Stored as JSON so we don't need a through model for what is
    # effectively a small, IP-scoped ledger.
    evidence = models.JSONField(
        default=dict,
        help_text=(
            "Map of state_code -> list of user UUIDs that voted "
            "for it on this IP."
        ),
    )

    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-confidence", "-last_seen_at"]

        indexes = [
            models.Index(fields=["state_code", "confidence"]),
            models.Index(fields=["last_seen_at"]),
        ]

        verbose_name = "IP State Mapping"
        verbose_name_plural = "IP State Mappings"

    def __str__(self):
        return f"{self.ip} -> {self.state_code} ({self.confidence})"

    # --------------------------------------------------------
    # Trust gate
    # --------------------------------------------------------

    @property
    def is_trusted(self):
        """
        Whether this mapping should be used in the lookup chain.
        """
        return self.confidence >= MIN_CONFIDENCE

    # --------------------------------------------------------
    # Evidence helpers
    # --------------------------------------------------------

    def users_for_state(self, state_code):
        """
        Return the list of user UUIDs that voted for a state.
        """
        raw = (self.evidence or {}).get(state_code, [])

        # Coerce to strings for consistent JSON storage.
        return [str(uid) for uid in raw]

    def has_user_voted_for_state(self, user_id, state_code):
        """
        Whether a specific user has already voted for a state.
        """
        return str(user_id) in self.users_for_state(state_code)

    def has_user_voted_anywhere(self, user_id):
        """
        Whether a specific user has already voted on this IP for
        any state. Used to enforce one-vote-per-user-per-IP.
        """
        user_key = str(user_id)

        for users in (self.evidence or {}).values():
            if user_key in [str(u) for u in users]:
                return True

        return False