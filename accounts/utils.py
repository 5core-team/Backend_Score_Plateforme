import secrets
import uuid
import os

from django.conf import settings
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes


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
# ENVOI DU LIEN DE SETUP MOT DE PASSE
# ─────────────────────────────────────────────

ROLE_LABELS = {
    'country':      'Représentant pays',
    'front office': 'Front Office',
    'huissier':     'Huissier',
    'conseiller':   'Conseiller financier',
    'admin':        'Administrateur',
}

def send_account_setup_email(user, token: str):
    """
    Envoie un email avec le lien unique de setup du mot de passe.
    Le message est adapté au rôle de l'utilisateur.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    setup_link   = f"{frontend_url}/account/setup/?uid={uid}&token={token}"

    # ✅ Message adapté au rôle — plus de "représentant pays" pour tous
    role_label = ROLE_LABELS.get(user.role, "utilisateur")

    subject = "Finalisation de votre compte Score"
    message = f"""
Bonjour {user.username},

Votre compte {role_label} a été créé avec succès sur la plateforme SCORE.

Pour finaliser votre inscription et définir votre mot de passe,
cliquez sur le lien ci-dessous :

{setup_link}

Ce lien est valable 24 heures.

Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.

Cordialement,
L'équipe SCORE
    """.strip()

    # ✅ Utilisation de send_email centralisé — plus de send_mail direct
    send_email({
        "subject": subject,
        "message": message,
        "to":      user.email,
    })


# ─────────────────────────────────────────────
# ENVOI EMAIL CRÉATION CLIENT
# ─────────────────────────────────────────────

def send_customer_creation_email(customer, huissier_username: str):
    """
    Envoie un email de notification au client après sa création par un huissier.
    Appelé depuis customers/serializers.py après la création du client.
    """
    send_email({
        "subject": "Création de votre dossier sur la plateforme SCORE",
        "message": f"""
Bonjour {customer.full_name},

Votre dossier a été créé avec succès sur la plateforme SCORE
par Maître {huissier_username}.

Vos informations enregistrées :
- Nom complet : {customer.full_name}
- NPI         : {customer.npi}
- Email       : {customer.email}

Si vous avez des questions ou si vous n'êtes pas à l'origine de cette démarche,
veuillez contacter directement votre huissier.

Cordialement,
L'équipe SCORE
        """.strip(),
        "to": customer.email,
    })