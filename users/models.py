from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from .manager import CustomUserManager
from django.conf import settings


class ScoreUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('admin', 'Administrateur'),
        ('conseiller', 'Conseiller financier'),
        ('huissier', 'Huissier'),
        ('country', 'Represantant pays'),
        ('front office', 'Reprentant_departement'),
        ('support', 'support_client',)
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    email = models.EmailField(max_length=100, unique=True)
    username = models.CharField(max_length=100, unique=True)
    password_changed = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ['email', 'role']

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Utilisateur personnalisé'
        verbose_name_plural = 'Utilisateurs personnalisés'


class Score(models.Model):
    user = models.OneToOneField(
        'ScoreUser',
        on_delete=models.CASCADE,
        related_name='score'
    )
    picture = models.ImageField(upload_to='scores/')  # chemin d'enregistrement dans MEDIA_ROOT

    def __str__(self):
        return f"Score de {self.user.username}"



class Support(models.Model):
    user = models.OneToOneField(
        'ScoreUser',
        on_delete=models.CASCADE,
        related_name='support'
    )
    document = models.FileField(upload_to='supports/', null=True, blank=True)  # ou ImageField si image uniquement

    def __str__(self):
        return f"Support de {self.user.username}"
