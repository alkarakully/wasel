from rest_framework import serializers

from .models import PhoneOTP, User
from .phone import InvalidPhone, normalize_iraqi_phone


class PhoneField(serializers.CharField):
    def to_internal_value(self, data):
        try:
            return normalize_iraqi_phone(super().to_internal_value(data))
        except InvalidPhone as error:
            raise serializers.ValidationError(str(error), code="invalid_phone")


class RequestCodeSerializer(serializers.Serializer):
    phone = PhoneField()
    channel = serializers.ChoiceField(choices=PhoneOTP.Channel.choices, default=PhoneOTP.Channel.WHATSAPP)


class VerifyCodeSerializer(serializers.Serializer):
    phone = PhoneField()
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "The code is 6 digits."})


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "phone", "name", "role", "language_pref"]
        read_only_fields = ["id", "phone", "role"]
