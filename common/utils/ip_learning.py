"""
IP -> state learning logic.

Records explicit user state selections as evidence on the
IPStateMapping table, and enforces the trust rules that decide
when an IP's state is authoritative.

SAFETY RULES (enforced here):
    1. Only explicit ?state= selections count.
    2. Only authenticated users count.
    3. Only phone-verified users count.
    4. Each user votes at most once per IP.
    5. A challenger state must exceed the incumbent by a safe
       margin before it replaces it.
    6. No vote is recorded when the IP is private/loopback.
"""

import ipaddress
import logging

from django.db import transaction

from common.models import (
    MIN_CONFIDENCE,
    IPStateMapping,
)
from common.constant import (
    STATE_CODE_TO_NAME,
    VALID_STATE_CODES,
)

logger = logging.getLogger(__name__)


# A challenger must exceed the incumbent by this many distinct
# users before it takes over. Prevents a single noisy voter from
# flipping a well-established mapping.
CHALLENGER_MARGIN = 3


# ------------------------------------------------------------
# Eligibility
# ------------------------------------------------------------

def _is_recordable_ip(ip):
    """
    Reject IPs we must never learn from.
    """

    if not ip:
        return False

    try:
        obj = ipaddress.ip_address(ip)
    except ValueError:
        return False

    if obj.is_private or obj.is_loopback or obj.is_link_local:
        return False

    return True


def _is_eligible_voter(user):
    """
    Only authenticated, phone-verified users contribute evidence.
    """

    if user is None:
        return False

    if not getattr(user, "is_authenticated", False):
        return False

    if not getattr(user, "is_phone_verified", False):
        return False

    return True


# ------------------------------------------------------------
# Record evidence
# ------------------------------------------------------------

def record_state_selection(user, ip, state_code):
    """
    Record a user's explicit state selection as evidence on the
    IP -> state mapping for `ip`.

    Safe to call on every ?state= request. No-ops when the user
    or IP is ineligible.

    Returns the resulting IPStateMapping instance, or None.
    """

    if not _is_recordable_ip(ip):
        return None

    if not _is_eligible_voter(user):
        return None

    if state_code not in VALID_STATE_CODES:
        return None

    user_key = str(user.pk)

    with transaction.atomic():

        mapping, _ = (
            IPStateMapping.objects
            .select_for_update()
            .get_or_create(
                ip=ip,
                defaults={
                    "state_code": state_code,
                    "confidence": 0,
                    "evidence": {},
                },
            )
        )

        evidence = dict(mapping.evidence or {})

        # ------------------------------------------------
        # Rule 4 — one vote per user per IP
        # ------------------------------------------------

        for existing_state, users in evidence.items():
            if user_key in [str(u) for u in users]:
                # Already voted on this IP. Ignore the repeat.
                return mapping

        # ------------------------------------------------
        # Append this vote
        # ------------------------------------------------

        voters = list(evidence.get(state_code, []))
        voters.append(user_key)
        evidence[state_code] = voters

        # ------------------------------------------------
        # Rule 5 — promotion / challenger logic
        # ------------------------------------------------

        incumbent = mapping.state_code
        incumbent_count = len(evidence.get(incumbent, []))
        challenger_count = len(voters)

        if state_code != incumbent:
            # Promote only if the challenger clears the margin.
            if challenger_count >= incumbent_count + CHALLENGER_MARGIN:
                mapping.state_code = state_code
                incumbent_count = challenger_count
            else:
                # Record the challenger's vote but do not flip.
                pass

        # Confidence reflects the incumbent's distinct-user count.
        mapping.evidence = evidence
        mapping.confidence = len(
            evidence.get(mapping.state_code, [])
        )

        mapping.save(
            update_fields=[
                "state_code",
                "confidence",
                "evidence",
                "last_seen_at",
            ]
        )

        if mapping.is_trusted:
            logger.info(
                "IPStateMapping promoted: %s -> %s (%d votes)",
                mapping.ip,
                mapping.state_code,
                mapping.confidence,
            )

        return mapping


# ------------------------------------------------------------
# Lookup
# ------------------------------------------------------------

def lookup_learned_state(ip):
    """
    Return the trusted learned state for an IP, or None.

    Only returns a value when the mapping has reached
    MIN_CONFIDENCE distinct verified voters.
    """

    if not _is_recordable_ip(ip):
        return None

    try:
        mapping = (
            IPStateMapping.objects
            .only("state_code", "confidence")
            .get(ip=ip)
        )
    except IPStateMapping.DoesNotExist:
        return None

    if mapping.confidence < MIN_CONFIDENCE:
        return None

    return mapping.state_code