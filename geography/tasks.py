from celery import shared_task
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def check_subscriptions():
    """
    Tâche quotidienne lancée chaque jour à minuit :
    - Envoie un email d'alerte 30 jours avant expiration
    - Bloque tous les utilisateurs dont l'abonnement a expiré
    """
    from .models import Country, Subscription
    from staff.models import FrontOffice, Huissier, FinancialAdvisor

    today      = now()
    alert_date = today + relativedelta(days=30)

    subscriptions = Subscription.objects.select_related(
        'country__manager'
    ).all()

    for subscription in subscriptions:
        country = subscription.country

        # ── Alerte 30 jours avant expiration ──────────────────────────
        if (
            subscription.expires_in and
            subscription.expires_in.date() == alert_date.date() and
            not subscription.is_blocked
        ):
            if country.manager:
                send_mail(
                    subject        = f"[SCORE] Renouvellement abonnement — {country.name}",
                    message        = (
                        f"Bonjour,\n\n"
                        f"L'abonnement de votre pays ({country.name}) expire le "
                        f"{subscription.expires_in.strftime('%d/%m/%Y')}.\n\n"
                        f"Il vous reste 30 jours pour renouveler votre abonnement "
                        f"et éviter toute interruption de service.\n\n"
                        f"Veuillez contacter l'administrateur de la plateforme SCORE "
                        f"pour procéder au renouvellement.\n\n"
                        f"Cordialement,\nL'équipe SCORE"
                    ),
                    from_email     = settings.EMAIL_HOST_USER,
                    recipient_list = [country.manager.email],
                    fail_silently  = True,
                )

        # ── Bloquer si abonnement expiré ──────────────────────────────
        if (
            subscription.expires_in and
            today > subscription.expires_in and
            not subscription.is_blocked
        ):
            # Marquer l'abonnement comme bloqué
            subscription.is_blocked = True
            subscription.save()

            # Collecter tous les utilisateurs du pays
            users_to_block = []

            if country.manager:
                users_to_block.append(country.manager)

            front_offices = FrontOffice.objects.filter(
                zone__country=country
            ).select_related('user')
            users_to_block += [fo.user for fo in front_offices]

            huissiers = Huissier.objects.filter(
                zone__country=country
            ).select_related('user')
            users_to_block += [h.user for h in huissiers]

            advisors = FinancialAdvisor.objects.filter(
                zone__country=country
            ).select_related('user')
            users_to_block += [a.user for a in advisors]

            # Désactiver tous les utilisateurs
            for user in users_to_block:
                user.is_active = False
                user.save()

            # Envoyer un email d'expiration au représentant pays
            if country.manager:
                send_mail(
                    subject        = f"[SCORE] Abonnement expiré — {country.name}",
                    message        = (
                        f"Bonjour,\n\n"
                        f"L'abonnement de votre pays ({country.name}) a expiré le "
                        f"{subscription.expires_in.strftime('%d/%m/%Y')}.\n\n"
                        f"Tous les comptes utilisateurs de votre pays ont été "
                        f"désactivés automatiquement.\n\n"
                        f"Veuillez contacter l'administrateur de la plateforme SCORE "
                        f"pour renouveler votre abonnement et réactiver vos comptes.\n\n"
                        f"Cordialement,\nL'équipe SCORE"
                    ),
                    from_email     = settings.EMAIL_HOST_USER,
                    recipient_list = [country.manager.email],
                    fail_silently  = True,
                )