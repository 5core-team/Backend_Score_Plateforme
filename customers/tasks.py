from celery import shared_task
from django.utils.timezone import now
from django.core.mail import send_mail
from django.conf import settings
from datetime import date, timedelta


def send_alert(subject, message, recipient_list):
    """Helper pour envoyer un email d'alerte."""
    send_mail(
        subject        = subject,
        message        = message,
        from_email     = settings.EMAIL_HOST_USER,
        recipient_list = recipient_list,
        fail_silently  = True,
    )


@shared_task
def check_debt_deadlines():
    """
    Tâche quotidienne lancée chaque jour à minuit.
    Gère les alertes préventives et les alertes de retard.
    """
    from .models import Debt

    today = now().date()

    # ── Dettes concernées ─────────────────────────────────────────────
    # Toutes les dettes validées et non remboursées
    debts = Debt.objects.filter(
        status='pending',
        validation_status='validated',
    ).select_related('customer', 'customer__huissier__user')

    for debt in debts:
        customer      = debt.customer
        huissier_user = customer.huissier.user if customer.huissier else None
        days_left     = (debt.deadline - today).days

        # ── ALERTES PRÉVENTIVES ───────────────────────────────────────
        if days_left in [7, 3, 1]:

            # Email au client
            send_alert(
                subject        = f"[SCORE] Rappel — Échéance dans {days_left} jour(s)",
                message        = (
                    f"Bonjour {customer.full_name},\n\n"
                    f"Nous vous rappelons que vous avez une dette dont l'échéance "
                    f"approche :\n\n"
                    f"- Montant        : {debt.amount}\n"
                    f"- Date d'échéance : {debt.deadline}\n"
                    f"- Jours restants  : {days_left} jour(s)\n\n"
                    f"Merci de procéder au remboursement avant la date d'échéance.\n\n"
                    f"Cordialement,\nL'équipe SCORE"
                ),
                recipient_list = [customer.email],
            )

            # Email à l'huissier si suivi activé
            if debt.is_monitored and huissier_user:
                send_alert(
                    subject        = f"[SCORE] Suivi — Échéance dans {days_left} jour(s) — {customer.full_name}",
                    message        = (
                        f"Bonjour,\n\n"
                        f"La dette suivante que vous surveillez arrive à échéance "
                        f"dans {days_left} jour(s) :\n\n"
                        f"- Client          : {customer.full_name}\n"
                        f"- Montant         : {debt.amount}\n"
                        f"- Date d'échéance  : {debt.deadline}\n\n"
                        f"Cordialement,\nL'équipe SCORE"
                    ),
                    recipient_list = [huissier_user.email],
                )

        # ── ALERTES DE RETARD ─────────────────────────────────────────
        elif today > debt.deadline:

            # Vérifier si on doit envoyer une alerte aujourd'hui
            # Jour J (première alerte) ou tous les 7 jours après
            should_alert = False

            if debt.last_alert_sent is None:
                # ✅ Première alerte — le jour J
                should_alert = True
            else:
                days_since_last_alert = (today - debt.last_alert_sent).days
                if days_since_last_alert >= 7:
                    # ✅ Alerte tous les 7 jours
                    should_alert = True

            if should_alert:
                days_overdue = (today - debt.deadline).days

                # Email au client
                send_alert(
                    subject        = f"[SCORE] RETARD — Votre dette est en retard de {days_overdue} jour(s)",
                    message        = (
                        f"Bonjour {customer.full_name},\n\n"
                        f"Votre dette est en retard de paiement :\n\n"
                        f"- Montant          : {debt.amount}\n"
                        f"- Date d'échéance   : {debt.deadline}\n"
                        f"- Jours de retard   : {days_overdue} jour(s)\n\n"
                        f"Merci de régulariser votre situation dans les plus brefs délais.\n\n"
                        f"Cordialement,\nL'équipe SCORE"
                    ),
                    recipient_list = [customer.email],
                )

                # Email à l'huissier si suivi activé
                if debt.is_monitored and huissier_user:
                    send_alert(
                        subject        = f"[SCORE] Suivi — RETARD {days_overdue} jour(s) — {customer.full_name}",
                        message        = (
                            f"Bonjour,\n\n"
                            f"La dette suivante que vous surveillez est en retard :\n\n"
                            f"- Client           : {customer.full_name}\n"
                            f"- Montant          : {debt.amount}\n"
                            f"- Date d'échéance   : {debt.deadline}\n"
                            f"- Jours de retard   : {days_overdue} jour(s)\n\n"
                            f"Cordialement,\nL'équipe SCORE"
                        ),
                        recipient_list = [huissier_user.email],
                    )

                # ✅ Mettre à jour la date de dernière alerte
                debt.last_alert_sent = today
                debt.save(update_fields=['last_alert_sent'])