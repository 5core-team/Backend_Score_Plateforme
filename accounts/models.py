from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from django.conf import settings
from .managers import CustomUserManager


# ─────────────────────────────────────────────
# SCORE USER
# ─────────────────────────────────────────────

class ScoreUser(AbstractBaseUser, PermissionsMixin):
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
    password_changed = models.BooleanField(default=False)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']

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
    user        = models.ForeignKey(ScoreUser, on_delete=models.CASCADE)
    token       = models.CharField(max_length=300)
    created_at  = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()

    @property
    def is_expired(self):
        return timezone.now() > self.expiry_date

    @property
    def is_valid(self):
        return (
            not self.is_expired and
            self.user.has_usable_password() and
            self.user.is_active
        )

    def __str__(self):
        return f"Credentials({self.user.email})"


# ─────────────────────────────────────────────
# PASSWORD RESET CODE
# ─────────────────────────────────────────────

class PasswordResetCodeModel(models.Model):
    user        = models.ForeignKey(ScoreUser, on_delete=models.CASCADE)
    code        = models.CharField(max_length=6)
    created_at  = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()

    def __str__(self):
        return f"ResetCode({self.user.email} - {self.code})"


# ─────────────────────────────────────────────
# PASSWORD CHANGE REQUEST
# ✅ Stocke le nouveau mot de passe hashé
# en attendant la confirmation par email (30 min)
# ─────────────────────────────────────────────

class PasswordChangeRequest(models.Model):
    user              = models.ForeignKey(ScoreUser, on_delete=models.CASCADE)
    new_password_hash = models.CharField(max_length=255)
    token             = models.CharField(max_length=100, unique=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    expiry_date       = models.DateTimeField()
    is_used           = models.BooleanField(default=False)

    @property
    def is_expired(self):
        return timezone.now() > self.expiry_date

    def __str__(self):
        return f"PasswordChangeRequest({self.user.email})"