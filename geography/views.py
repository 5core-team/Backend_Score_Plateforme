from django.shortcuts import get_object_or_404

from rest_framework import viewsets, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.exceptions import PermissionDenied

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse

from .models import Country, Zone, SubZone
from .serializers import CountrySerializer, ZoneSerializer, SubZoneSerializer


# ─────────────────────────────────────────────
# PERMISSIONS PERSONNALISÉES
# ─────────────────────────────────────────────

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser


class IsCountryRepresentant(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'country'


class IsFrontOffice(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'front office'


# ─────────────────────────────────────────────
# COUNTRY VIEWSET
# ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=["Geography - Country"],
        summary="Lister tous les pays",
        description="Accessible à tous les utilisateurs authentifiés.",
        responses={200: CountrySerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Geography - Country"],
        summary="Récupérer un pays",
        responses={
            200: CountrySerializer,
            404: OpenApiResponse(description="Pays non trouvé"),
        },
    ),
    create=extend_schema(
        tags=["Geography - Country"],
        summary="Créer un pays",
        description="Réservé au super admin uniquement.",
        request=CountrySerializer,
        responses={
            201: OpenApiResponse(description="Pays créé avec succès"),
            400: OpenApiResponse(description="Données invalides"),
            403: OpenApiResponse(description="Permission refusée"),
        },
    ),
    update=extend_schema(
        tags=["Geography - Country"],
        summary="Modifier un pays (complet)",
        description="Réservé au super admin uniquement.",
        request=CountrySerializer,
        responses={
            200: CountrySerializer,
            400: OpenApiResponse(description="Données invalides"),
            404: OpenApiResponse(description="Pays non trouvé"),
        },
    ),
    partial_update=extend_schema(
        tags=["Geography - Country"],
        summary="Modifier un pays (partiel)",
        description="Réservé au super admin uniquement.",
        request=CountrySerializer,
        responses={
            200: CountrySerializer,
            404: OpenApiResponse(description="Pays non trouvé"),
        },
    ),
    destroy=extend_schema(
        tags=["Geography - Country"],
        summary="Supprimer un pays",
        description="Réservé au super admin uniquement.",
        responses={
            204: OpenApiResponse(description="Pays supprimé"),
            404: OpenApiResponse(description="Pays non trouvé"),
        },
    ),
)
class CountryViewSet(viewsets.ViewSet):
    serializer_class   = CountrySerializer
    lookup_value_regex = r'\d+'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    def list(self, request: Request):
        countries  = Country.objects.all()
        serializer = CountrySerializer(countries, many=True)
        return Response(serializer.data)

    def retrieve(self, request: Request, pk=None):
        country    = get_object_or_404(Country, pk=pk)
        serializer = CountrySerializer(country)
        return Response(serializer.data)

    def create(self, request: Request):
        serializer = CountrySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response({"msg": "Country successfully created."}, status=status.HTTP_201_CREATED)

    def update(self, request: Request, pk=None):
        country    = get_object_or_404(Country, pk=pk)
        # ✅ instance passée pour que validate() ignore email/username/iso_code existants
        serializer = CountrySerializer(country, data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request: Request, pk=None):
        country    = get_object_or_404(Country, pk=pk)
        # ✅ instance passée pour que validate() ignore email/username/iso_code existants
        serializer = CountrySerializer(country, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request: Request, pk=None):
        country = get_object_or_404(Country, pk=pk)
        country.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
# ZONE VIEWSET
# Créé par : Représentant Pays
# ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=["Geography - Zone"],
        summary="Lister les zones",
        description="Super admin → toutes | Représentant pays → ses zones uniquement",
        responses={200: ZoneSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Geography - Zone"],
        summary="Récupérer une zone",
        responses={200: ZoneSerializer, 404: OpenApiResponse(description="Zone non trouvée")},
    ),
    create=extend_schema(
        tags=["Geography - Zone"],
        summary="Créer une zone",
        description="Réservé au représentant pays uniquement. Le pays est déduit automatiquement.",
        request=ZoneSerializer,
        responses={
            201: ZoneSerializer,
            400: OpenApiResponse(description="Données invalides"),
            403: OpenApiResponse(description="Permission refusée"),
        },
    ),
    update=extend_schema(
        tags=["Geography - Zone"],
        summary="Modifier une zone (complet)",
        request=ZoneSerializer,
        responses={200: ZoneSerializer},
    ),
    partial_update=extend_schema(
        tags=["Geography - Zone"],
        summary="Modifier une zone (partiel)",
        request=ZoneSerializer,
        responses={200: ZoneSerializer},
    ),
    destroy=extend_schema(
        tags=["Geography - Zone"],
        summary="Supprimer une zone",
        responses={204: OpenApiResponse(description="Zone supprimée")},
    ),
)
class ZoneViewSet(viewsets.ModelViewSet):
    serializer_class   = ZoneSerializer
    lookup_value_regex = r'\d+'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # ✅ Seul le représentant pays crée/modifie/supprime les zones
            return [IsCountryRepresentant()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Zone.objects.all()

        if user.role == 'country':
            try:
                country = Country.objects.get(manager=user)
                return Zone.objects.filter(country=country)
            except Country.DoesNotExist:
                return Zone.objects.none()

        if user.role in ['front office', 'huissier', 'conseiller']:
            from staff.models import FrontOffice, Huissier, FinancialAdvisor
            if user.role == 'front office':
                fo = FrontOffice.objects.filter(user=user).first()
                return Zone.objects.filter(country=fo.zone.country) if fo else Zone.objects.none()
            if user.role == 'huissier':
                h = Huissier.objects.filter(user=user).first()
                return Zone.objects.filter(country=h.zone.country) if h else Zone.objects.none()
            if user.role == 'conseiller':
                fa = FinancialAdvisor.objects.filter(user=user).first()
                return Zone.objects.filter(country=fa.zone.country) if fa else Zone.objects.none()

        return Zone.objects.none()

    def create(self, request, *args, **kwargs):
        # ✅ Le pays est déduit automatiquement depuis le représentant pays connecté
        try:
            country = Country.objects.get(manager=request.user)
        except Country.DoesNotExist:
            raise PermissionDenied("Vous n'êtes manager d'aucun pays.")

        data = request.data.copy()
        data['country'] = country.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────
# SUBZONE VIEWSET
# Créé par : Front Office
# ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=["Geography - SubZone"],
        summary="Lister les sous-zones",
        description="Super admin → toutes | Représentant pays → ses sous-zones | Front office / Huissier / Conseiller → sous-zones de leur pays",
        responses={200: SubZoneSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Geography - SubZone"],
        summary="Récupérer une sous-zone",
        responses={200: SubZoneSerializer, 404: OpenApiResponse(description="Sous-zone non trouvée")},
    ),
    create=extend_schema(
        tags=["Geography - SubZone"],
        summary="Créer une sous-zone",
        description="Réservé au front office uniquement. La zone doit correspondre à sa zone de gestion.",
        request=SubZoneSerializer,
        responses={
            201: SubZoneSerializer,
            400: OpenApiResponse(description="Données invalides ou zone non autorisée"),
            403: OpenApiResponse(description="Permission refusée"),
        },
    ),
    update=extend_schema(
        tags=["Geography - SubZone"],
        summary="Modifier une sous-zone (complet)",
        request=SubZoneSerializer,
        responses={200: SubZoneSerializer},
    ),
    partial_update=extend_schema(
        tags=["Geography - SubZone"],
        summary="Modifier une sous-zone (partiel)",
        request=SubZoneSerializer,
        responses={200: SubZoneSerializer},
    ),
    destroy=extend_schema(
        tags=["Geography - SubZone"],
        summary="Supprimer une sous-zone",
        responses={204: OpenApiResponse(description="Sous-zone supprimée")},
    ),
)
class SubZoneViewSet(viewsets.ModelViewSet):
    serializer_class   = SubZoneSerializer
    lookup_value_regex = r'\d+'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # ✅ Correction : c'est le Front Office qui gère les sous-zones
            return [IsFrontOffice()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return SubZone.objects.all()

        if user.role == 'country':
            try:
                country = Country.objects.get(manager=user)
                return SubZone.objects.filter(zone__country=country)
            except Country.DoesNotExist:
                return SubZone.objects.none()

        if user.role in ['front office', 'huissier', 'conseiller']:
            from staff.models import FrontOffice, Huissier, FinancialAdvisor
            if user.role == 'front office':
                fo = FrontOffice.objects.filter(user=user).first()
                return SubZone.objects.filter(zone__country=fo.zone.country) if fo else SubZone.objects.none()
            if user.role == 'huissier':
                h = Huissier.objects.filter(user=user).first()
                return SubZone.objects.filter(zone=h.subZone.zone) if h and h.subZone else SubZone.objects.none()
            if user.role == 'conseiller':
                fa = FinancialAdvisor.objects.filter(user=user).first()
                return SubZone.objects.filter(zone__country=fa.zone.country) if fa else SubZone.objects.none()

        return SubZone.objects.none()

    def create(self, request, *args, **kwargs):
        from staff.models import FrontOffice

        # ✅ Récupérer le front office connecté
        try:
            front_office = FrontOffice.objects.get(user=request.user)
        except FrontOffice.DoesNotExist:
            return Response(
                {"error": "Aucun profil front office associé à votre compte."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Vérifier que la zone appartient bien à la zone du front office
        zone_id = request.data.get('zone')
        if not zone_id:
            return Response(
                {"error": "Le champ 'zone' est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            zone = Zone.objects.get(id=zone_id)
        except Zone.DoesNotExist:
            return Response(
                {"error": "Zone introuvable."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if zone != front_office.zone:
            return Response(
                {"error": "Cette zone ne correspond pas à votre zone de gestion."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)