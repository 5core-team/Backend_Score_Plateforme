from django.db import models
from users.models import ScoreUser
from django.utils.timezone import now


class Country(models.Model):

    name = models.CharField(max_length=255, unique=True, null=True, blank=True)
    country_code = models.CharField(max_length=10, unique=True)
    licence_status = models.BooleanField(default=False)
    phone_code = models.CharField(max_length=10)
    user = models.OneToOneField(ScoreUser, on_delete=models.CASCADE)  # Liaison à un utilisateur (qui peut se connecter)

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "Pays"
        verbose_name_plural = "Pays"


class Subscription(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='subscriptions')
    # title = models.CharField(max_length=255)
    # document = models.FileField(upload_to='certificates/')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_in = models.DateTimeField()

    def __str__(self):
        return f"Certificate for {self.country.name} (Expires on {self.expires_in})"
    
    def is_active(self):
        return now() < self.expires_in


class FrontOffice(models.Model):
    name = models.CharField(max_length=255)
    # localisation = models.CharField(max_length=255)
    npi = models.CharField(verbose_name="Numéro de pièce d'identité", max_length=200, default="0")
    phone = models.CharField(verbose_name="Numéro de téléphone", max_length=100)
    user = models.OneToOneField(ScoreUser, on_delete=models.CASCADE)  # Liaison à un utilisateur (qui peut se connecter)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)  # Liaison à un pays

    def __str__(self):
        return self.name

class AvailableZone(models.Model):
    name = models.CharField(max_length=500)
    front_office = models.ForeignKey(FrontOffice, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Huissier(models.Model):
    user = models.OneToOneField(ScoreUser, on_delete=models.CASCADE, related_name='huissier')
    front_office = models.ForeignKey(FrontOffice, on_delete=models.CASCADE)  # Liaison au front office qui l’a créé
    npi = models.CharField(max_length=100)
    phone = models.CharField(max_length=200, verbose_name="Numéro de téléphone", default="00000")
    picture = models.ImageField(upload_to='huissiers/', null=True, blank=True)
    zone = models.CharField(max_length=500, verbose_name="Zone de front office", default="")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username


class Financial(models.Model):
    user = models.OneToOneField(ScoreUser, on_delete=models.CASCADE, related_name='financial_profile')
    front_office = models.ForeignKey(FrontOffice, on_delete=models.CASCADE)  # Liaison au front office qui l’a créé
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=100, default="00000")
    picture = models.ImageField(upload_to='financials/', null=True, blank=True)
    npi = models.CharField(max_length=100)

    def __str__(self):
        return self.name
