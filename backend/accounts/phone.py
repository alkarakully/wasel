import re

# Arabic-Indic and Eastern Arabic-Indic (Persian/Kurdish keyboards) digits.
_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

# Iraqi mobile numbers: 7 followed by an operator digit 3-9, then 8 digits.
_IRAQI_MOBILE = re.compile(r"^7[3-9]\d{8}$")


class InvalidPhone(ValueError):
    pass


def other_phone(raw):
    """
    Any other phone number, tidied (spaces, dashes and brackets removed,
    Arabic-Indic digits converted), or None if it isn't one. Only staff
    accounts, which don't sign in by code, may use these.
    """
    tidy = re.sub(r"[\s\-()]", "", str(raw or "")).translate(_DIGIT_MAP)
    return tidy if re.fullmatch(r"\+?\d{6,15}", tidy) else None


def normalize_iraqi_phone(raw):
    """
    Return an Iraqi mobile number in E.164 form (+9647XXXXXXXXX).

    Accepts 07XX..., 7XX..., 9647XX..., +9647XX... and 009647XX..., with
    spaces, dashes or brackets, in Western or Arabic-Indic digits.
    """
    digits = re.sub(r"[\s\-()]", "", str(raw or "")).translate(_DIGIT_MAP)
    if digits.startswith("+"):
        digits = digits[1:]
    elif digits.startswith("00"):
        digits = digits[2:]

    if digits.startswith("964"):
        digits = digits[3:]
    elif digits.startswith("0"):
        digits = digits[1:]

    if not _IRAQI_MOBILE.match(digits):
        raise InvalidPhone("Enter an Iraqi mobile number starting with 07.")
    return f"+964{digits}"
