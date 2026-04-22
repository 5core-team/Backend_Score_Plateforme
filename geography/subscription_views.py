from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta
from django.conf import settings
from drf_spectacular.utils import extend_schema

from .models import Country, Subscription
from .views import IsSuperAdmin
from staff.models import FrontOffice, Huissier, FinancialAdvisor
from accounts.utils import send_email


# ─────────────────────────────────────────────
# HELPER — Récupérer tous les utilisateurs d'un pays
# ─────────────────────────────────────────────

def get_country_users(country):
    """Retourne tous les utilisateurs liés à un pays."""
    users = []

    if country.manager:
        users.append(country.manager)

    front_offices = FrontOffice.objects.filter(zone__country=country).select_related('user')
    users += [fo.user for fo in front_offices]

    huissiers = Huissier.objects.filter(zone__country=country).select_related('user')
    users += [h.user for h in huissiers]

    advisors = FinancialAdvisor.objects.filter(zone__country=country).select_related('user')
    users += [a.user for a in advisors]

    return users


# ─────────────────────────────────────────────
# CRÉER UN ABONNEMENT
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Geography - Country"],
    summary="Créer l'abonnement d'un pays",
    description="Réservé au super admin. Démarre un abonnement d'un an pour le pays.",
    request=None,
    responses=None,
)
class CreateSubscriptionView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, country_id):
        try:
            country = Country.objects.get(id=country_id)
        except Country.DoesNotExist:
            return Response(
                {"error": "Pays introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        if hasattr(country, 'subscription'):
            return Response(
                {"error": "Ce pays a déjà un abonnement. Utilisez l'endpoint de renouvellement."},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription = Subscription.objects.create(
            country    = country,
            starts_at  = now(),
            expires_in = now() + relativedelta(years=1),
            is_blocked = False,
        )

        # ✅ Activer le représentant pays
        if country.manager:
            country.manager.is_active = True
            country.manager.save()

        # ✅ Envoi via send_email centralisé — plus de send_mail direct
        if country.manager:
            send_email({
                "subject": f"[SCORE] Abonnement activé — {country.name}",
                "message": (
                    f"Bonjour,\n\n"
                    f"L'abonnement de votre pays ({country.name}) a été activé avec succès.\n\n"
                    f"Date de début     : {subscription.starts_at.strftime('%d/%m/%Y')}\n"
                    f"Date d'expiration : {subscription.expires_in.strftime('%d/%m/%Y')}\n\n"
                    f"Cordialement,\nL'équipe SCORE"
                ),
                "to": country.manager.email,
            })

        return Response({
            "message":    f"Abonnement créé pour {country.name}.",
            "starts_at":  subscription.starts_at,
            "expires_in": subscription.expires_in,
        }, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────
# RENOUVELER UN ABONNEMENT
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Geography - Country"],
    summary="Renouveler l'abonnement d'un pays",
    description="Réservé au super admin. Renouvelle l'abonnement pour 1 an supplémentaire.",
    request=None,
    responses=None,
)
class RenewSubscriptionView(APIView):
    permission_classes = [IsSuperAdmin]

    def put(self, request, country_id):
        try:
            country = Country.objects.get(id=country_id)
        except Country.DoesNotExist:
            return Response(
                {"error": "Pays introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not hasattr(country, 'subscription'):
            return Response(
                {"error": "Aucun abonnement trouvé. Créez d'abord un abonnement."},
                status=status.HTTP_404_NOT_FOUND
            )

        subscription            = country.subscription
        subscription.expires_in = now() + relativedelta(years=1)
        subscription.is_blocked = False
        subscription.save()

        # ✅ Réactiver tous les utilisateurs du pays
        for user in get_country_users(country):
            user.is_active = True
            user.save()

        # ✅ Envoi via send_email centralisé
        if country.manager:
            send_email({
                "subject": f"[SCORE] Abonnement renouvelé — {country.name}",
                "message": (
                    f"Bonjour,\n\n"
                    f"L'abonnement de votre pays ({country.name}) a été renouvelé avec succès.\n\n"
                    f"Nouvelle date d'expiration : {subscription.expires_in.strftime('%d/%m/%Y')}\n\n"
                    f"Cordialement,\nL'équipe SCORE"
                ),
                "to": country.manager.email,
            })

        return Response({
            "message":        f"Abonnement renouvelé pour {country.name}.",
            "new_expires_in": subscription.expires_in,
        }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# DÉTAIL ABONNEMENT
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Geography - Country"],
    summary="Détail de l'abonnement d'un pays",
    description="Réservé au super admin. Retourne les détails de l'abonnement d'un pays.",
    responses=None,
)
class SubscriptionDetailView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, country_id):
        try:
            country = Country.objects.get(id=country_id)
        except Country.DoesNotExist:
            return Response(
                {"error": "Pays introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not hasattr(country, 'subscription'):
            return Response(
                {"error": "Aucun abonnement trouvé pour ce pays."},
                status=status.HTTP_404_NOT_FOUND
            )

        subscription = country.subscription

        return Response({
            "country":    country.name,
            "is_active":  subscription.is_active(),
            "is_blocked": subscription.is_blocked,
            "starts_at":  subscription.starts_at,
            "expires_in": subscription.expires_in,
            "created_at": subscription.created_at,
        }, status=status.HTTP_200_OK)