from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, BasePermission, SAFE_METHODS
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiResponse

from .models import FrontOffice, Huissier, FinancialAdvisor
from .serializers import FrontOfficeSerializer, HuissierSerializer, FinancialAdvisorSerializer


# ─────────────────────────────────────────────
# PERMISSIONS PERSONNALISÉES
# ─────────────────────────────────────────────

class IsSuperAdmin(BasePermission):
    """Seul le super admin."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser


class IsCountryRepresentant(BasePermission):
    """Seul le représentant pays."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'country'


class IsFrontOffice(BasePermission):
    """Seul le front office."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'front office'


class IsHuissier(BasePermission):
    """Seul l'huissier."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'huissier'


# ─────────────────────────────────────────────
# FRONT OFFICE
# Créé par : Représentant Pays
# ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=["Staff - Front Office"],
        summary="Lister les front offices",
        description="Super admin → tous | Représentant pays → son pays uniquement",
    ),
    retrieve=extend_schema(
        tags=["Staff - Front Office"],
        summary="Récupérer un front office",
    ),
    create=extend_schema(
        tags=["Staff - Front Office"],
        summary="Créer un front office",
        description="Réservé au représentant pays uniquement.",
    ),
    update=extend_schema(
        tags=["Staff - Front Office"],
        summary="Modifier un front office",
        description="Réservé au représentant pays uniquement.",
    ),
    partial_update=extend_schema(
        tags=["Staff - Front Office"],
        summary="Modifier partiellement un front office",
    ),
    destroy=extend_schema(
        tags=["Staff - Front Office"],
        summary="Supprimer un front office",
        description="Réservé au représentant pays uniquement.",
    ),
)
class FrontOfficeViewSet(viewsets.ModelViewSet):
    serializer_class = FrontOfficeSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsCountryRepresentant()]  # ✅ seul le représentant pays
        return [IsAuthenticated()]            # lecture pour tous les authentifiés

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return FrontOffice.objects.all()

        if user.role == 'country':
            # Le représentant voit seulement les front offices de son pays
            return FrontOffice.objects.filter(zone__country=user.country)

        if user.role == 'front office':
            # Le front office se voit lui-même
            return FrontOffice.objects.filter(user=user)

        return FrontOffice.objects.none()


# ─────────────────────────────────────────────
# HUISSIER
# Créé par : Front Office
# ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=["Staff - Huissier"],
        summary="Lister les huissiers",
        description="Super admin → tous | Représentant pays → son pays | Front office → sa zone",
    ),
    retrieve=extend_schema(
        tags=["Staff - Huissier"],
        summary="Récupérer un huissier",
    ),
    create=extend_schema(
        tags=["Staff - Huissier"],
        summary="Créer un huissier",
        description="Réservé au front office uniquement.",
    ),
    update=extend_schema(
        tags=["Staff - Huissier"],
        summary="Modifier un huissier",
        description="Réservé au front office uniquement.",
    ),
    partial_update=extend_schema(
        tags=["Staff - Huissier"],
        summary="Modifier partiellement un huissier",
    ),
    destroy=extend_schema(
        tags=["Staff - Huissier"],
        summary="Supprimer un huissier",
        description="Réservé au front office uniquement.",
    ),
)
class HuissierViewSet(viewsets.ModelViewSet):
    serializer_class = HuissierSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsFrontOffice()]   # ✅ seul le front office
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Huissier.objects.all()

        if user.role == 'country':
            return Huissier.objects.filter(zone__country=user.country)

        if user.role == 'front office':
            # Le front office voit les huissiers de sa zone
            front_office = FrontOffice.objects.filter(user=user).first()
            if front_office:
                return Huissier.objects.filter(zone=front_office.zone)

        if user.role == 'huissier':
            # L'huissier se voit lui-même
            return Huissier.objects.filter(user=user)

        return Huissier.objects.none()


# ─────────────────────────────────────────────
# FINANCIAL ADVISOR
# Créé par : Front Office
# Consulte uniquement les clients (pas de création)
# ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=["Staff - Conseiller Financier"],
        summary="Lister les conseillers financiers",
        description="Super admin → tous | Représentant pays → son pays | Front office → sa zone",
    ),
    retrieve=extend_schema(
        tags=["Staff - Conseiller Financier"],
        summary="Récupérer un conseiller financier",
    ),
    create=extend_schema(
        tags=["Staff - Conseiller Financier"],
        summary="Créer un conseiller financier",
        description="Réservé au front office uniquement.",
    ),
    update=extend_schema(
        tags=["Staff - Conseiller Financier"],
        summary="Modifier un conseiller financier",
        description="Réservé au front office uniquement.",
    ),
    partial_update=extend_schema(
        tags=["Staff - Conseiller Financier"],
        summary="Modifier partiellement un conseiller financier",
    ),
    destroy=extend_schema(
        tags=["Staff - Conseiller Financier"],
        summary="Supprimer un conseiller financier",
        description="Réservé au front office uniquement.",
    ),
)
class FinancialAdvisorViewSet(viewsets.ModelViewSet):
    serializer_class = FinancialAdvisorSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsFrontOffice()]   # ✅ seul le front office
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return FinancialAdvisor.objects.all()

        if user.role == 'country':
            return FinancialAdvisor.objects.filter(zone__country=user.country)

        if user.role == 'front office':
            # Le front office voit les conseillers de sa zone
            front_office = FrontOffice.objects.filter(user=user).first()
            if front_office:
                return FinancialAdvisor.objects.filter(zone=front_office.zone)

        if user.role == 'conseiller':
            # Le conseiller se voit lui-même
            return FinancialAdvisor.objects.filter(user=user)

        return FinancialAdvisor.objects.none()
    
class FrontOfficeViewSet(viewsets.ModelViewSet):
    serializer_class   = FrontOfficeSerializer
    lookup_value_regex = r'\d+'  # ✅
    ...

class HuissierViewSet(viewsets.ModelViewSet):
    serializer_class   = HuissierSerializer
    lookup_value_regex = r'\d+'  # ✅
    ...

class FinancialAdvisorViewSet(viewsets.ModelViewSet):
    serializer_class   = FinancialAdvisorSerializer
    lookup_value_regex = r'\d+'  # ✅