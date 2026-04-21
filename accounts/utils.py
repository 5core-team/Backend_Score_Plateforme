import secrets
import uuid
import os

from django.conf import settings
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes


def send_account_setup_email(user, token: str):
    uid = urlsafe_base64_encode(force_bytes(user.pk))

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


def send_customer_creation_email(customer, huissier_username: str):
    """
    Envoie un email de notification au client après sa création par un huissier.

    Appelé depuis customers/serializers.py après la création du client.
    """
    subject = "Création de votre dossier sur la plateforme SCORE"
    message = f"""
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
    """.strip()

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[customer.email],
        fail_silently=False,
    )


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