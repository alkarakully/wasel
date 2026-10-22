from rest_framework import serializers

from .models import PhoneOTP, User
from .phone import InvalidPhone, normalize_phone
from regions.countries import BY_CODE


class PhoneField(serializers.CharField):
    """A mobile number in E.164, read in the country sent alongside it (`country`, Iraq by default)."""

    def to_internal_value(self, data):
        country = "IQ"
        initial = getattr(self.parent, "initial_data", None)
        if hasattr(initial, "get"):
            country = str(initial.get("country") or "IQ").upper()
        try:
            return normalize_phone(super().to_internal_value(data), country)
        except InvalidPhone as error:
            raise serializers.ValidationError(str(error), code="invalid_phone")


class CountryField(serializers.ChoiceField):
    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("default", "IQ")
        super().__init__(choices=list(BY_CODE), **kwargs)

    def to_internal_value(self, data):
        return super().to_internal_value(str(data or "IQ").upper())


class _PhoneOrEmail(serializers.Serializer):
    """A phone number (WhatsApp) or an email address; exactly one."""

    phone = PhoneField(required=False)
    email = serializers.EmailField(required=False)
    country = CountryField()

    def validate(self, data):
        if bool(data.get("phone")) == bool(data.get("email")):
            raise serializers.ValidationError({"phone": "Enter a phone number or an email."})
        if data.get("email"):
            data["email"] = data["email"].strip().lower()
        return data


class RequestCodeSerializer(_PhoneOrEmail):
    # Optional: the address says it all. Kept so apps can be explicit.
    channel = serializers.ChoiceField(choices=PhoneOTP.Channel.choices, required=False)

    def validate(self, data):
        data = super().validate(data)
        data["channel"] = PhoneOTP.Channel.EMAIL if data.get("email") else PhoneOTP.Channel.WHATSAPP
        return data


class VerifyCodeSerializer(_PhoneOrEmail):
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "The code is 6 digits."})


class PasswordLoginSerializer(serializers.Serializer):
    # A phone number (read in `country`) or an email.
    login = serializers.CharField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)
    country = CountryField()


class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class EmailCodeSerializer(EmailSerializer):
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "The code is 6 digits."})


class UserSerializer(serializers.ModelSerializer):
    # Whether password sign-in is set up (the password itself never leaves the server).
    has_password = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "phone", "email", "has_password", "name", "role", "language_pref", "country"]
        read_only_fields = ["id", "phone", "email", "role", "country"]

    def get_has_password(self, user):
        return user.has_usable_password()
