import uuid
import os
import secrets

from django.conf import settings
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from rest_framework import serializers


# ─────────────────────────────────────────────
# GESTION DES FICHIERS MÉDIAS
# ─────────────────────────────────────────────

def get_media_url(file):
    """Retourne l'URL complète d'un fichier média."""
    request = None  # si pas de request disponible
    return f"{settings.MEDIA_HOST}{file.url}" if hasattr(settings, 'MEDIA_HOST') else file.url


def create_file(filebuffer):
    """Renomme un fichier uploadé avec un UUID unique."""
    ext = os.path.splitext(filebuffer.name)[1]
    filebuffer.name = f"{uuid.uuid4()}{ext}"
    return filebuffer


# ─────────────────────────────────────────────
# SERIALIZER FICHIER
# ─────────────────────────────────────────────

class FileSerializer(serializers.Field):
    def to_internal_value(self, data):
        return data  # ✅ retourne la donnée brute pour traitement

    def to_representation(self, value):
        if not value:
            return None
        return get_media_url(value)


# ─────────────────────────────────────────────
# GÉNÉRATION DE CODE ALÉATOIRE
# ─────────────────────────────────────────────

def generate_random_code():
    """Génère un code aléatoire URL-safe."""
    return secrets.token_urlsafe(8)


# ─────────────────────────────────────────────
# ENVOI D'EMAIL GÉNÉRIQUE
# ─────────────────────────────────────────────

def send_email(data: dict):
    """
    Envoie un email simple.
    data = {
        "subject": "...",
        "message": "...",
        "to": "destinataire@email.com"
    }
    """
    send_mail(
        subject=data.get("subject"),
        message=data.get("message"),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[data.get("to")],
        fail_silently=False,
    )


# ─────────────────────────────────────────────
# ENVOI DU LIEN DE SETUP MOT DE PASSE  ✅ NOUVEAU
# ─────────────────────────────────────────────

def send_account_setup_email(user, token: str):
    """
    Envoie un email avec le lien unique de setup du mot de passe.

    Le lien généré :
    frontend.com/account/setup/?uid=<uid_encodé>&token=<token>

    Appelé après la création d'un représentant pays.
    """
    # Encoder l'ID utilisateur en base64 (sécurisé)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    # URL frontend de setup (configurable dans settings.py)
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    setup_link = f"{frontend_url}/account/setup/?uid={uid}&token={token}"

    subject = "Finalisation de votre compte Score"
    message = f"""
Bonjour {user.username},

Votre compte représentant pays a été créé avec succès.

Pour finaliser votre inscription et définir votre mot de passe,
cliquez sur le lien ci-dessous :

{setup_link}

Ce lien est valable 24 heures.

Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.

Cordialement,
L'équipe Score
    """.strip()

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        fail_silently=False,
    )