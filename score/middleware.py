from django.http import JsonResponse
from django.utils.timezone import now
from rest_framework_simplejwt.authentication import JWTAuthentication


# ─────────────────────────────────────────────
# CHEMINS EXEMPTÉS DE LA VÉRIFICATION
# ─────────────────────────────────────────────

EXEMPT_PATHS = [
    '/api/auth/login/',
    '/api/auth/verify-code/',
    '/api/auth/reset-code/',
    '/api/auth/reset-password/',
    '/api/auth/verify-credentials/',
    '/api/auth/password-setup/',
    '/api/schema/',
    '/api/docs/',
    '/api/redoc/',
    '/admin/',
]


class SubscriptionMiddleware:
    """
    Vérifie à chaque requête si l'abonnement du pays
    de l'utilisateur connecté est actif.
    Bloque l'accès si expiré ou désactivé.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # ── Ignorer les chemins exemptés ──────────────────────────────
        if any(request.path.startswith(path) for path in EXEMPT_PATHS):
            return self.get_response(request)

        # ── Authentifier l'utilisateur via JWT ────────────────────────
        try:
            auth   = JWTAuthentication()
            result = auth.authenticate(request)
            if result is None:
                return self.get_response(request)
            user, _ = result
        except Exception:
            return self.get_response(request)

        # ── Super admin — toujours autorisé ───────────────────────────
        if user.is_superuser:
            return self.get_response(request)

        # ── Récupérer le pays de l'utilisateur ────────────────────────
        country = self._get_user_country(user)
        if country is None:
            return self.get_response(request)

        # ── Vérifier que le pays a un abonnement ──────────────────────
        if not hasattr(country, 'subscription'):
            return JsonResponse(
                {"error": "Votre pays n'a pas d'abonnement actif. Veuillez contacter l'administrateur."},
                status=403
            )

        # ── Vérifier que l'abonnement est actif ───────────────────────
        subscription = country.subscription
        if not subscription.is_active():
            return JsonResponse(
                {"error": "L'abonnement de votre pays a expiré. Veuillez contacter l'administrateur."},
                status=403
            )

        return self.get_response(request)

    # ─────────────────────────────────────────────
    # HELPER — Récupérer le pays de l'utilisateur
    # ─────────────────────────────────────────────

    def _get_user_country(self, user):
        """Retourne le pays associé à l'utilisateur selon son rôle."""
        from geography.models import Country
        from staff.models import FrontOffice, Huissier, FinancialAdvisor

        if user.role == 'country':
            return Country.objects.filter(manager=user).first()

        if user.role == 'front office':
            fo = FrontOffice.objects.filter(user=user).select_related('zone__country').first()
            return fo.zone.country if fo else None

        if user.role == 'huissier':
            h = Huissier.objects.filter(user=user).select_related('zone__country').first()
            return h.zone.country if h else None

        if user.role == 'conseiller':
            a = FinancialAdvisor.objects.filter(user=user).select_related('zone__country').first()
            return a.zone.country if a else None

        return None