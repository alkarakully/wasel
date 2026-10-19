import re

from regions.countries import BY_CODE, MOBILE_RULES, country_for_dial, dial_code

# Arabic-Indic and Eastern Arabic-Indic (Persian/Kurdish keyboards) digits.
_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_ANY_MOBILE = r"\d{6,14}"


class InvalidPhone(ValueError):
    pass


def _tidy(raw):
    return re.sub(r"[\s\-().]", "", str(raw or "")).translate(_DIGIT_MAP)


def other_phone(raw):
    """
    Any phone number, tidied (spaces, dashes and brackets removed, Arabic-Indic
    digits converted), or None if it isn't one. Staff accounts, which sign in
    to the Django admin with a password, may store these as typed.
    """
    tidy = _tidy(raw)
    return tidy if re.fullmatch(r"\+?\d{6,15}", tidy) else None


def _mobile_ok(country, national):
    return re.fullmatch(MOBILE_RULES.get(country, _ANY_MOBILE), national) is not None


def normalize_phone(raw, country="IQ"):
    """
    A mobile number in E.164 form (+9647XXXXXXXXX, +9665XXXXXXXX, ...).

    International input (+966..., 00966...) says its own country; anything
    else is read as a national number of `country` (Iraq by default), with
    or without the leading 0. Spaces, dashes, brackets and Arabic-Indic
    digits are fine.
    """
    country = (country or "IQ").upper()
    if country not in BY_CODE:
        raise InvalidPhone("Choose the country of this number.")
    digits = _tidy(raw)
    international = digits.startswith("+") or digits.startswith("00")
    digits = digits.lstrip("+")
    if digits.startswith("00"):
        digits = digits[2:]
    if not digits.isdigit():
        raise InvalidPhone(_message(country))

    if international:
        found, dial = country_for_dial(digits)
        if found is None:
            raise InvalidPhone("This country code isn't one we know.")
        # A shared code (+1, +7) belongs to the chosen country when it shares it.
        if dial_code(country) == dial:
            found = country
        national = digits[len(dial):]
    else:
        found, dial = country, dial_code(country)
        # People often type the country code without the +.
        if digits.startswith(dial) and _mobile_ok(country, digits[len(dial):]):
            digits = digits[len(dial):]
        national = digits[1:] if digits.startswith("0") else digits

    if not _mobile_ok(found, national):
        raise InvalidPhone(_message(found))
    return f"+{dial}{national}"


def country_of(phone):
    """The country of an E.164 number we stored (Iraq if unclear)."""
    found, _ = country_for_dial(str(phone or "").lstrip("+"))
    return found or "IQ"


def _message(country):
    name = BY_CODE[country][2]
    if country == "IQ":
        return "Enter an Iraqi mobile number starting with 07."
    return f"Enter a mobile number from {name}."


def normalize_iraqi_phone(raw):
    """Kept for older callers: normalize_phone() for Iraq."""
    return normalize_phone(raw, "IQ")
