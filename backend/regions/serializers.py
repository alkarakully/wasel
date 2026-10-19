from rest_framework import serializers

from .regions import as_api, for_currency, quantize


class MoneyMixin:
    """
    Money fields as strings with exactly their currency's decimals ("18000",
    "12.50", "0.750"), next to a "currency" field when the serializer lists one.
    """

    money_fields = ()

    def currency_for(self, instance):
        return instance.currency

    def to_representation(self, instance):
        data = super().to_representation(instance)
        currency = self.currency_for(instance)
        for name in self.money_fields:
            if data.get(name) is not None:
                data[name] = as_api(data[name], currency)
        return data


def check_amount(value, currency):
    """Refuse amounts finer than the currency allows (half a dinar, a tenth of a fils)."""
    if value != quantize(value, currency):
        decimals = for_currency(currency).decimals
        raise serializers.ValidationError(
            "Use whole amounts." if decimals == 0 else f"Use at most {decimals} decimals."
        )
    return value
