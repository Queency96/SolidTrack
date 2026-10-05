"""
Nigerian states with ISO 3166-2:NG codes.

The code is the value MaxMind GeoLite2 returns in the `region`
field. Codes match ISO 3166-2:NG, which Nigerian states follow.

Source: ISO 3166-2:NG
"""

NIGERIA_STATE_CHOICES = (
    ("AB", "Abia"),
    ("AD", "Adamawa"),
    ("AK", "Akwa Ibom"),
    ("AN", "Anambra"),
    ("BA", "Bauchi"),
    ("BY", "Bayelsa"),
    ("BE", "Benue"),
    ("BO", "Borno"),
    ("CR", "Cross River"),
    ("DE", "Delta"),
    ("EB", "Ebonyi"),
    ("ED", "Edo"),
    ("EK", "Ekiti"),
    ("EN", "Enugu"),
    ("FC", "Federal Capital Territory"),
    ("GO", "Gombe"),
    ("IM", "Imo"),
    ("JI", "Jigawa"),
    ("KD", "Kaduna"),
    ("KN", "Kano"),
    ("KT", "Katsina"),
    ("KE", "Kebbi"),
    ("KO", "Kogi"),
    ("KW", "Kwara"),
    ("LA", "Lagos"),
    ("NA", "Nasarawa"),
    ("NI", "Niger"),
    ("OG", "Ogun"),
    ("ON", "Ondo"),
    ("OS", "Osun"),
    ("OY", "Oyo"),
    ("PL", "Plateau"),
    ("RI", "Rivers"),
    ("SO", "Sokoto"),
    ("TA", "Taraba"),
    ("YO", "Yobe"),
    ("ZA", "Zamfara"),
)

STATE_CODE_TO_NAME = dict(NIGERIA_STATE_CHOICES)

# Uppercase canonical names -> code. Handles both "Lagos" and "LAGOS".
STATE_NAME_TO_CODE = {
    name.upper(): code for code, name in NIGERIA_STATE_CHOICES
}

# Some MaxMind region values use slightly different spellings.
# Add aliases here so lookups never miss.
STATE_NAME_ALIASES = {
    "ABUJA": "FC",
    "FCT": "FC",
    "FEDERAL CAPITAL TERRITORY": "FC",
    "AKWA-IBOM": "AK",
    "CROSS-RIVER": "CR",
}

VALID_STATE_CODES = set(STATE_CODE_TO_NAME.keys())


def normalize_state(value):
    """
    Return the ISO code for a state given either a code or a name.

    Accepts:
        "LA", "la", "Lagos", "LAGOS", "Abuja", "FCT"

    Returns:
        Two-letter ISO code, or None if unrecognized.
    """

    if not value:
        return None

    candidate = str(value).strip().upper()

    if not candidate:
        return None

    # Direct code match
    if candidate in VALID_STATE_CODES:
        return candidate

    # Alias match
    if candidate in STATE_NAME_ALIASES:
        return STATE_NAME_ALIASES[candidate]

    # Full name match
    if candidate in STATE_NAME_TO_CODE:
        return STATE_NAME_TO_CODE[candidate]

    return None