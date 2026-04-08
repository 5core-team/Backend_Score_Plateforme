from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin  # ✅ PermissionsMixin ajouté
from django.utils import timezone
from django.conf import settings
from .managers import CustomUserManager


# ─────────────────────────────────────────────
# SCORE USER
# ─────────────────────────────────────────────

class ScoreUser(AbstractBaseUser, PermissionsMixin):  # ✅ PermissionsMixin ajouté
    ROLE_CHOICES = (
        ('admin',        'Administrateur'),
        ('conseiller',   'Conseiller financier'),
        ('huissier',     'Huissier'),
        ('country',      'Représentant pays'),
        ('front office', 'Représentant département'),
    )

    role     = models.CharField(max_length=20, choices=ROLE_CHOICES)
    email    = models.EmailField(max_length=100, unique=True)
    username = models.CharField(max_length=100)
    photo    = models.ImageField(upload_to='profile_photos/', null=True, blank=True)

    is_active        = models.BooleanField(default=True)
    is_staff         = models.BooleanField(default=False)
    password_changed = models.BooleanField(default=False)  # ✅ ajouté

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']  # ✅ username et non role

    objects = CustomUserManager()

    class Meta:
        verbose_name        = 'Utilisateur personnalisé'
        verbose_name_plural = 'Utilisateurs personnalisés'

    def __str__(self):
        return f"{self.email} ({self.role})"


# ─────────────────────────────────────────────
# ACCOUNT CREDENTIALS
# ─────────────────────────────────────────────

class AccountCredentials(models.Model):
    user       = models.ForeignKey(ScoreUser, on_delete=models.CASCADE)
    token      = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()  # ✅ ajouté — utilisé dans toutes vos vues

    @property
    def is_expired(self):
        return timezone.now() > self.expiry_date  # ✅ timezone.now() correct

    @property
    def is_valid(self):
        return (                                   # ✅ return ajouté
            not self.is_expired and
            self.user.has_usable_password() and
            self.user.is_active
        )

    def __str__(self):
        return f"Credentials({self.user.email})"
    

class PasswordResetCodeModel(models.Model):
    user        = models.ForeignKey(ScoreUser, on_delete=models.CASCADE)
    code        = models.CharField(max_length=6)
    created_at  = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()

    def __str__(self):
        return f"ResetCode({self.user.email} - {self.code})"