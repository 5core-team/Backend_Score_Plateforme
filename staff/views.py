from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiResponse

from .models import FrontOffice, Huissier, FinancialAdvisor
from .serializers import FrontOfficeSerializer, HuissierSerializer, FinancialAdvisorSerializer
from geography.models import SubZone


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
# HELPER — Validation SubZone
# ─────────────────────────────────────────────

def validate_subzone_belongs_to_front_office(subzone_id, front_office):
    """
    Vérifie que la subzone appartient bien
    à la zone du front office connecté.
    """
    if not subzone_id:
        return None, None

    try:
        subzone = SubZone.objects.get(id=subzone_id)
    except SubZone.DoesNotExist:
        return None, "Sous-zone introuvable."

    if subzone.zone != front_office.zone:
        return None, "Cette sous-zone n'appartient pas à votre zone."

    return subzone, None


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
    serializer_class   = FrontOfficeSerializer
    lookup_value_regex = r'\d+'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsCountryRepresentant()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return FrontOffice.objects.all()

        if user.role == 'country':
            from geography.models import Country
            try:
                country = Country.objects.get(manager=user)
                return FrontOffice.objects.filter(zone__country=country)
            except Country.DoesNotExist:
                return FrontOffice.objects.none()

        if user.role == 'front office':
            return FrontOffice.objects.filter(user=user)

        return FrontOffice.objects.none()


# ─────────────────────────────────────────────
# HUISSIER
# Créé par : Front Office
# SubZone doit appartenir à la Zone du Front Office
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
        description="Réservé au front office. La subZone doit appartenir à sa zone.",
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
    serializer_class   = HuissierSerializer
    lookup_value_regex = r'\d+'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsFrontOffice()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Huissier.objects.all()

        if user.role == 'country':
            from geography.models import Country
            try:
                country = Country.objects.get(manager=user)
                return Huissier.objects.filter(zone__country=country)
            except Country.DoesNotExist:
                return Huissier.objects.none()

        if user.role == 'front office':
            front_office = FrontOffice.objects.filter(user=user).first()
            if front_office:
                return Huissier.objects.filter(zone=front_office.zone)
            return Huissier.objects.none()

        if user.role == 'huissier':
            return Huissier.objects.filter(user=user)

        return Huissier.objects.none()

    def create(self, request, *args, **kwargs):
        # ✅ Vérifier que la subZone appartient à la zone du front office
        front_office = FrontOffice.objects.filter(user=request.user).first()
        if not front_office:
            return Response(
                {"error": "Vous n'êtes associé à aucun front office."},
                status=status.HTTP_400_BAD_REQUEST
            )

        subzone_id = request.data.get('subZone')
        if subzone_id:
            _, error = validate_subzone_belongs_to_front_office(subzone_id, front_office)
            if error:
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Forcer la zone du front office
        data = request.data.copy()
        data['zone'] = front_office.zone.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────
# FINANCIAL ADVISOR
# Créé par : Front Office
# SubZone doit appartenir à la Zone du Front Office
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
        description="Réservé au front office. La subZone doit appartenir à sa zone.",
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
    serializer_class   = FinancialAdvisorSerializer
    lookup_value_regex = r'\d+'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsFrontOffice()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return FinancialAdvisor.objects.all()

        if user.role == 'country':
            from geography.models import Country
            try:
                country = Country.objects.get(manager=user)
                return FinancialAdvisor.objects.filter(zone__country=country)
            except Country.DoesNotExist:
                return FinancialAdvisor.objects.none()

        if user.role == 'front office':
            front_office = FrontOffice.objects.filter(user=user).first()
            if front_office:
                return FinancialAdvisor.objects.filter(zone=front_office.zone)
            return FinancialAdvisor.objects.none()

        if user.role == 'conseiller':
            return FinancialAdvisor.objects.filter(user=user)

        return FinancialAdvisor.objects.none()

    def create(self, request, *args, **kwargs):
        # ✅ Vérifier que la subZone appartient à la zone du front office
        front_office = FrontOffice.objects.filter(user=request.user).first()
        if not front_office:
            return Response(
                {"error": "Vous n'êtes associé à aucun front office."},
                status=status.HTTP_400_BAD_REQUEST
            )

        subzone_id = request.data.get('subZone')
        if subzone_id:
            _, error = validate_subzone_belongs_to_front_office(subzone_id, front_office)
            if error:
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Forcer la zone du front office
        data = request.data.copy()
        data['zone'] = front_office.zone.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)