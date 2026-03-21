from rest_framework import serializers
from .models import Country, Subscription, AvailableZone


class SubscriptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subscription
        fields = ["created_at", "expires_in"]

class CountrySerializer(serializers.ModelSerializer):
    subscriptions = SubscriptionSerializer(many=True)
    class Meta:
        model = Country
        fields = ["name", "country_code", "phone_code", "subscriptions"]


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableZone
        fields = ["name"]

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'  # ou ['name', 'country_code', 'phone_code', ...]
