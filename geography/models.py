from django.db import models
from accounts.models import ScoreUser

class Country(models.Model):
    name = models.CharField(max_length=255)
    iso_code = models.CharField(max_length=10, unique=True)
    manager = models.OneToOneField(ScoreUser, on_delete=models.SET_NULL, null=True) # Manager can be null

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def has_valid_subscription(self):
        """
        Return True when a country has a valid subscription
        """
        pass

class Zone(models.Model):
    name = models.CharField(max_length=255)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='zones')

    class Meta:
        unique_together = ['name', 'country'] # Ensure that zones are uniques for each country

class SubZone(models.Model):
    name = models.CharField(max_length=255)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='subzones')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='subzones')

    class Meta:
        unique_together = ['name', 'zone'] # Ensure that sub zones are uniques for each zone
