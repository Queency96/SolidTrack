"""
IP geolocation chain with a learned Nigeria-specific tier.

Chain (highest to lowest priority):
    Tier 0 — ?state= query override
    Tier 1 — IPStateMapping (learned, >=5 verified votes)
    Tier 2 — GeoLite2 (offline .mmdb)
    Tier 3 — FreeIPAPI (HTTPS, 60/min, commercial OK)
    Tier 4 — ip-api.com (HTTP, 45/min, non-commercial)
    Tier 5 — User.state (profile)
    Tier 6 — None (frontend prompts)
"""

import ipaddress
import logging

import requests
from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2
from django.core.cache import cache

from common.constant import (
    STATE_CODE_TO_NAME,
    normalize_state,
)
from common.utils.ip_learning import (
    lookup_learned_state,
    record_state_selection,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

GEOIP_CACHE_PREFIX = "geoip:state:"
GEOIP_CACHE_TIMEOUT = 5 * 60

PROVIDER_BLOCK_PREFIX = "geoip:blocked:"
PROVIDER_BLOCK_TIMEOUT = 60

IPAPI_URL = "http://ip-api.com/json/{ip}"
FREEIPAPI_URL = "https://freeipapi.com/api/json/{ip}"

REQUEST_TIMEOUT = 3


# ------------------------------------------------------------
# Client IP
# ------------------------------------------------------------

def get_client_ip(request):
    """
    Return the authoritative client IP, or None.

    SECURITY: does not read HTTP_X_FORWARDED_FOR directly.
    Uses django-ipware with the trusted-proxy precedence.
    """

    if request is None:
        return None

    try:
        from ipware import get_client_ip as _ipware_get
    except ImportError:
        return request.META.get("REMOTE_ADDR") or None

    client_ip, _ = _ipware_get(request)

    if not client_ip:
        return None

    try:
        ip_obj = ipaddress.ip_address(client_ip)
    except ValueError:
        return None

    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
        return None

    return client_ip


# ------------------------------------------------------------
# Tier 2 — GeoLite2
# ------------------------------------------------------------

_geoip_instance = None


def _get_geoip():
    global _geoip_instance

    if _geoip_instance is None:
        try:
            _geoip_instance = GeoIP2()
        except Exception:
            logger.exception(
                "GeoIP2 could not be initialised. Check GEOIP_PATH."
            )
            _geoip_instance = False

    return _geoip_instance or None


def _lookup_maxmind(ip):
    geoip = _get_geoip()
    if geoip is None:
        return None

    try:
        data = geoip.city(ip)
    except Exception:
        return None

    if not data or data.get("country_code") != "NG":
        return None

    region = data.get("region")
    if not region:
        return None

    return normalize_state(region)


# ------------------------------------------------------------
# Online provider helpers
# ------------------------------------------------------------

def _provider_blocked(provider):
    return cache.get(f"{PROVIDER_BLOCK_PREFIX}{provider}") is True


def _mark_provider_blocked(provider):
    cache.set(
        f"{PROVIDER_BLOCK_PREFIX}{provider}",
        True,
        PROVIDER_BLOCK_TIMEOUT,
    )


# ------------------------------------------------------------
# Tier 3 — FreeIPAPI
# ------------------------------------------------------------

def _lookup_freeipapi(ip):

    if _provider_blocked("freeipapi"):
        return None

    try:
        response = requests.get(
            FREEIPAPI_URL.format(ip=ip),
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        logger.exception("FreeIPAPI request failed for %s", ip)
        return None

    if response.status_code == 429:
        logger.warning("FreeIPAPI rate limit hit — blocking 60s")
        _mark_provider_blocked("freeipapi")
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    if data.get("countryCode") != "NG":
        return None

    for key in ("regionCode", "regionName", "region"):
        code = normalize_state(data.get(key))
        if code:
            return code

    return None


# ------------------------------------------------------------
# Tier 4 — ip-api.com
# ------------------------------------------------------------

def _lookup_ipapi(ip):

    if _provider_blocked("ipapi"):
        return None

    try:
        response = requests.get(
            IPAPI_URL.format(ip=ip),
            params={
                "fields": "status,countryCode,region,regionName",
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        logger.exception("ip-api.com request failed for %s", ip)
        return None

    if response.status_code == 429:
        logger.warning("ip-api.com rate limit hit — blocking 60s")
        _mark_provider_blocked("ipapi")
        return None

    if response.status_code != 200:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    if data.get("status") != "success":
        return None

    if data.get("countryCode") != "NG":
        return None

    for key in ("region", "regionName"):
        code = normalize_state(data.get(key))
        if code:
            return code

    return None


# ------------------------------------------------------------
# Chained IP lookup
# ------------------------------------------------------------

def get_ip_state_code(request):
    """
    Return the state code for the client IP, or None.

    Chain:
        Tier 1 — IPStateMapping (learned, trusted only)
        Tier 2 — GeoLite2
        Tier 3 — FreeIPAPI
        Tier 4 — ip-api.com

    Cached per-IP for GEOIP_CACHE_TIMEOUT seconds.
    """

    ip = get_client_ip(request)
    if not ip:
        return None

    cache_key = f"{GEOIP_CACHE_PREFIX}{ip}"
    cached = cache.get(cache_key)

    if cached is not None:
        return cached or None

    code = (
        lookup_learned_state(ip)       # Tier 1
        or _lookup_maxmind(ip)         # Tier 2
        or _lookup_freeipapi(ip)       # Tier 3
        or _lookup_ipapi(ip)           # Tier 4
    )

    cache.set(cache_key, code or "", GEOIP_CACHE_TIMEOUT)

    return code


# ------------------------------------------------------------
# User persistence (profile-level)
# ------------------------------------------------------------

def _persist_user_state(user, state_code):
    """
    Persist an explicit state selection to User.state.

    Only called for logged-in users with a valid code.
    """

    if user is None or not user.is_authenticated:
        return

    state_name = STATE_CODE_TO_NAME.get(state_code, "")

    if not state_name:
        return

    if (getattr(user, "state", "") or "").strip() == state_name:
        return

    try:
        user.state = state_name
        user.save(update_fields=["state"])
    except Exception:
        logger.exception(
            "Failed to persist User.state for user=%s",
            getattr(user, "pk", None),
        )


def _persist_last_ip(user, ip):
    if user is None or not user.is_authenticated:
        return
    if not ip:
        return
    if getattr(user, "last_detected_ip", None) == ip:
        return

    try:
        user.last_detected_ip = ip
        user.save(update_fields=["last_detected_ip"])
    except Exception:
        logger.exception(
            "Failed to persist User.last_detected_ip for user=%s",
            getattr(user, "pk", None),
        )


# ------------------------------------------------------------
# Top-level resolver
# ------------------------------------------------------------

def resolve_browse_state(request):
    """
    Resolve the state code used to scope the product list.

    Precedence:
        Tier 0 — ?state=<code|name>
        Tier 1 — learned IP mapping
        Tier 2 — GeoLite2
        Tier 3 — FreeIPAPI
        Tier 4 — ip-api.com
        Tier 5 — User.state
        Tier 6 — None

    Returns (state_code_or_None, source).
    Source is one of: "query", "learned", "ip", "user", "none".
    """

    user = getattr(request, "user", None)
    ip = get_client_ip(request)

    # --------------------------------------------------------
    # Tier 0 — explicit override
    # --------------------------------------------------------

    raw = (request.query_params.get("state") or "").strip()

    if raw:
        code = normalize_state(raw)

        if code:
            # Per-user preference
            _persist_user_state(user, code)

            # Aggregated learning — only fires for verified users
            record_state_selection(user, ip, code)

            return code, "query"

    # --------------------------------------------------------
    # Tier 1 — learned mapping
    # --------------------------------------------------------

    if ip:
        learned = lookup_learned_state(ip)
        if learned:
            return learned, "learned"

    # --------------------------------------------------------
    # Tier 2-4 — external providers
    # --------------------------------------------------------

    if ip:
        provider_code = (
            _lookup_maxmind(ip)
            or _lookup_freeipapi(ip)
            or _lookup_ipapi(ip)
        )

        if provider_code:
            _persist_last_ip(user, ip)
            return provider_code, "ip"

    # --------------------------------------------------------
    # Tier 5 — profile
    # --------------------------------------------------------

    if user is not None and user.is_authenticated:
        profile_code = normalize_state(getattr(user, "state", ""))
        if profile_code:
            return profile_code, "user"

    # --------------------------------------------------------
    # Tier 6 — nothing
    # --------------------------------------------------------

    return None, "none"