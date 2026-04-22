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
# La zone est déduite automatiquement depuis le pays du représentant
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
        description="Réservé au représentant pays uniquement. La zone est déduite automatiquement — le frontend envoie : email, username, name, npi, phone.",
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

    def create(self, request, *args, **kwargs):
        from geography.models import Country, Zone

        # ✅ Récupérer le pays du représentant pays connecté
        try:
            country = Country.objects.get(manager=request.user)
        except Country.DoesNotExist:
            raise PermissionDenied("Vous n'êtes manager d'aucun pays.")

        # ✅ Le représentant pays peut préciser la zone via zone_id (optionnel)
        zone_id = request.data.get('zone_id')
        if zone_id:
            try:
                zone = Zone.objects.get(id=zone_id, country=country)
            except Zone.DoesNotExist:
                return Response(
                    {"error": "Zone introuvable ou n'appartient pas à votre pays."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            zone = Zone.objects.filter(country=country).first()
            if not zone:
                return Response(
                    {"error": "Aucune zone disponible dans votre pays."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # ✅ Zone injectée via save() — le frontend n'envoie pas ce champ
        serializer.save(zone=zone)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────
# HUISSIER
# Créé par : Front Office
# Zone déduite automatiquement depuis le front office connecté
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
        description="Réservé au front office. La zone est déduite automatiquement. La subZone doit appartenir à la zone du front office. Le frontend envoie : email, username, name, subZone, npi, phone, picture.",
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
        # ✅ Récupérer le front office connecté
        front_office = FrontOffice.objects.filter(user=request.user).first()
        if not front_office:
            return Response(
                {"error": "Vous n'êtes associé à aucun front office."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Vérifier que la subZone appartient à la zone du front office
        subzone_id = request.data.get('subZone')
        if subzone_id:
            subzone, error = validate_subzone_belongs_to_front_office(subzone_id, front_office)
            if error:
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # ✅ Zone injectée via save() — le frontend n'envoie pas ce champ
        serializer.save(zone=front_office.zone)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────
# FINANCIAL ADVISOR
# Créé par : Front Office
# Zone déduite automatiquement depuis le front office connecté
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
        description="Réservé au front office. La zone est déduite automatiquement. La subZone doit appartenir à la zone du front office. Le frontend envoie : email, username, name, subZone, npi, phone, picture.",
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
        # ✅ Récupérer le front office connecté
        front_office = FrontOffice.objects.filter(user=request.user).first()
        if not front_office:
            return Response(
                {"error": "Vous n'êtes associé à aucun front office."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Vérifier que la subZone appartient à la zone du front office
        subzone_id = request.data.get('subZone')
        if subzone_id:
            subzone, error = validate_subzone_belongs_to_front_office(subzone_id, front_office)
            if error:
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # ✅ Zone injectée via save() — le frontend n'envoie pas ce champ
        serializer.save(zone=front_office.zone)
        return Response(serializer.data, status=status.HTTP_201_CREATED)