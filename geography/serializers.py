from .models import Country
from accounts.models import ScoreUser, AccountCredentials
from rest_framework import serializers
from django.db import transaction
import secrets

class CountrySerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=100)

    class Meta:
        model = Country
        fields = ['name', 'iso_code']
        extras_fields = ['email', 'username']
    
    def validate(self, attrs: dict):
        data = super().validate(attrs)
        email = data.get('email')

        # Check if user exists
        if (ScoreUser.objects.filter(email=email).exists()):
            raise serializers.ValidationError({'email': 'Account already exists'})
        
        # Check if country exists
        if (Country.objects.filter(iso_code=data.get('iso_code')).exists()):
            raise serializers.ValidationError({
                'iso_code': 'This country already exists'
            })
        return data

    @transaction.atomic
    def create(self, validated_data: dict):
        
        # Create user
        user = ScoreUser(
            email=validated_data.pop('email'),
            username=validated_data.pop('username'),
            role='country',
            is_active=False
        )
        user.set_unusable_password()
        user.save()

        # Create Account credentials
        AccountCredentials.objects.create(
            user=user,
            token=secrets.token_urlsafe(32)
        )

        # Create country
        country = Country.objects.create(
            iso_code=validated_data.pop('iso_code'),
            name=validated_data.pop('name'),
            manager=user
        )
        return country


        
