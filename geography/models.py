from django.db import models
from django.utils.timezone import now
from accounts.models import ScoreUser


# ─────────────────────────────────────────────
# COUNTRY
# ─────────────────────────────────────────────

class Country(models.Model):
    name           = models.CharField(max_length=255)
    iso_code       = models.CharField(max_length=10, unique=True)
    phone_code     = models.CharField(max_length=10, null=True, blank=True)  # ✅ ajouté
    licence_status = models.BooleanField(default=False)                       # ✅ ajouté
    manager        = models.OneToOneField(ScoreUser, on_delete=models.SET_NULL, null=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.iso_code})"

    @property
    def has_valid_subscription(self):
        # ✅ implémenté — vérifie si une souscription active existe
        return self.subscriptions.filter(expires_in__gt=now()).exists()

    class Meta:
        verbose_name        = "Pays"
        verbose_name_plural = "Pays"


# ─────────────────────────────────────────────
# SUBSCRIPTION  ✅ nouveau modèle
# ─────────────────────────────────────────────

class Subscription(models.Model):
    country    = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='subscriptions')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_in = models.DateTimeField()

    def __str__(self):
        return f"Subscription({self.country.name} - expire: {self.expires_in})"

    def is_active(self):
        return now() < self.expires_in

    class Meta:
        verbose_name        = "Abonnement"
        verbose_name_plural = "Abonnements"


# ─────────────────────────────────────────────
# ZONE
# ─────────────────────────────────────────────

class Zone(models.Model):
    name    = models.CharField(max_length=255)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='zones')

    class Meta:
        unique_together = ['name', 'country']
        verbose_name        = "Zone"
        verbose_name_plural = "Zones"

    def __str__(self):
        return f"{self.name} - {self.country.name}"


# ─────────────────────────────────────────────
# SUBZONE
# ─────────────────────────────────────────────

class SubZone(models.Model):
    name = models.CharField(max_length=255)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='subzones')

    class Meta:
        unique_together     = ['name', 'zone']
        verbose_name        = "Sous-zone"
        verbose_name_plural = "Sous-zones"

    def __str__(self):
        return f"{self.name} - {self.zone.name}"