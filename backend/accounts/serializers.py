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


class RequestCodeSerializer(serializers.Serializer):
    phone = PhoneField()
    country = CountryField()
    channel = serializers.ChoiceField(choices=PhoneOTP.Channel.choices, default=PhoneOTP.Channel.WHATSAPP)


class VerifyCodeSerializer(serializers.Serializer):
    phone = PhoneField()
    country = CountryField()
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "The code is 6 digits."})


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "phone", "name", "role", "language_pref", "country"]
        read_only_fields = ["id", "phone", "role", "country"]
