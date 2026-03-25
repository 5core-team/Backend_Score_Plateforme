from django.db import models

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from .managers import CustomUserManager
from django.conf import settings
import datetime as dt


class ScoreUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('admin', 'Administrateur'),
        ('conseiller', 'Conseiller financier'),
        ('huissier', 'Huissier'),
        ('country', 'Represantant pays'),
        ('front office', 'Reprentant_departement'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    email = models.EmailField(max_length=100, unique=True)
    username = models.CharField(max_length=100, unique=False)
    photo = models.ImageField(upload_to='profile_photos/', null=True,blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['role']

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Utilisateur personnalisé'
        verbose_name_plural = 'Utilisateurs personnalisés'

class AccountCredentials(models.Model):
    token = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(ScoreUser, on_delete=models.CASCADE)

    @property
    def is_expired(self):
        expiration_delay = dt.timedelta(hours=24)
        return dt.timezone.now() > (self.created_at + expiration_delay)
    
    @property
    def is_valid(self):
        self.user.has_usable_password() and self.user.is_active
