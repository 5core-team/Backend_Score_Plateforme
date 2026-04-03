from django.shortcuts import get_object_or_404

from rest_framework import viewsets, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse

from .models import Country, Zone, SubZone
from .serializers import CountrySerializer, ZoneSerializer, SubZoneSerializer


# ─────────────────────────────────────────────
# COUNTRY VIEWSET  (ViewSet simple → annoter chaque action)
# ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=["Country"],
        summary="Lister tous les pays",
        responses={200: CountrySerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Country"],
        summary="Récupérer un pays",
        responses={
            200: CountrySerializer,
            404: OpenApiResponse(description="Pays non trouvé"),
        },
    ),
    create=extend_schema(
        tags=["Country"],
        summary="Créer un pays",
        request=CountrySerializer,
        responses={
            201: OpenApiResponse(description="Pays créé avec succès"),
            400: OpenApiResponse(description="Données invalides"),
        },
    ),
    update=extend_schema(
        tags=["Country"],
        summary="Modifier un pays (remplacement complet)",
        request=CountrySerializer,
        responses={
            200: CountrySerializer,
            400: OpenApiResponse(description="Données invalides"),
            404: OpenApiResponse(description="Pays non trouvé"),
        },
    ),
    partial_update=extend_schema(
        tags=["Country"],
        summary="Modifier un pays (partiel)",
        request=CountrySerializer,
        responses={
            200: CountrySerializer,
            400: OpenApiResponse(description="Données invalides"),
            404: OpenApiResponse(description="Pays non trouvé"),
        },
    ),
    destroy=extend_schema(
        tags=["Country"],
        summary="Supprimer un pays",
        responses={
            204: OpenApiResponse(description="Pays supprimé"),
            404: OpenApiResponse(description="Pays non trouvé"),
        },
    ),
)
class CountryViewSet(viewsets.ViewSet):
    """ViewSet CRUD pour les pays — accès admin uniquement."""

    permission_classes = [IsAdminUser]
    serializer_class = CountrySerializer  # utilisé par Swagger comme hint

    def list(self, request: Request):
        countries = Country.objects.all()
        serializer = CountrySerializer(countries, many=True)
        return Response(serializer.data)

    def retrieve(self, request: Request, pk=None):
        country = get_object_or_404(Country, pk=pk)
        serializer = CountrySerializer(country)
        return Response(serializer.data)

    def create(self, request: Request):
        serializer = CountrySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response({"msg": "Country successfully created."}, status=status.HTTP_201_CREATED)

    def update(self, request: Request, pk=None):
        country = get_object_or_404(Country, pk=pk)
        serializer = CountrySerializer(country, data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request: Request, pk=None):
        country = get_object_or_404(Country, pk=pk)
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
# ZONE VIEWSET  (ModelViewSet → @extend_schema_view sur la classe)
# ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=["Zone"],
        summary="Lister les zones du pays de l'utilisateur",
        responses={200: ZoneSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Zone"],
        summary="Récupérer une zone",
        responses={200: ZoneSerializer, 404: OpenApiResponse(description="Zone non trouvée")},
    ),
    create=extend_schema(
        tags=["Zone"],
        summary="Créer une zone",
        request=ZoneSerializer,
        responses={201: ZoneSerializer, 400: OpenApiResponse(description="Données invalides")},
    ),
    update=extend_schema(
        tags=["Zone"],
        summary="Modifier une zone (complet)",
        request=ZoneSerializer,
        responses={200: ZoneSerializer},
    ),
    partial_update=extend_schema(
        tags=["Zone"],
        summary="Modifier une zone (partiel)",
        request=ZoneSerializer,
        responses={200: ZoneSerializer},
    ),
    destroy=extend_schema(
        tags=["Zone"],
        summary="Supprimer une zone",
        responses={204: OpenApiResponse(description="Zone supprimée")},
    ),
)
class ZoneViewSet(viewsets.ModelViewSet):
    """Gestion des zones — accès limité au pays de l'utilisateur connecté."""

    serializer_class = ZoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Zone.objects.filter(country=self.request.user.country)

    def perform_create(self, serializer):
        serializer.save(country=self.request.user.country)


# ─────────────────────────────────────────────
# SUBZONE VIEWSET  (ModelViewSet → @extend_schema_view sur la classe)
# ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=["SubZone"],
        summary="Lister les sous-zones accessibles",
        description="Admin/staff → toutes les sous-zones. Country user → ses sous-zones uniquement.",
        responses={200: SubZoneSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["SubZone"],
        summary="Récupérer une sous-zone",
        responses={200: SubZoneSerializer, 404: OpenApiResponse(description="Sous-zone non trouvée")},
    ),
    create=extend_schema(
        tags=["SubZone"],
        summary="Créer une sous-zone",
        request=SubZoneSerializer,
        responses={
            201: SubZoneSerializer,
            400: OpenApiResponse(description="Données invalides"),
            403: OpenApiResponse(description="Permission refusée"),
        },
    ),
    update=extend_schema(
        tags=["SubZone"],
        summary="Modifier une sous-zone (complet)",
        request=SubZoneSerializer,
        responses={200: SubZoneSerializer, 403: OpenApiResponse(description="Permission refusée")},
    ),
    partial_update=extend_schema(
        tags=["SubZone"],
        summary="Modifier une sous-zone (partiel)",
        request=SubZoneSerializer,
        responses={200: SubZoneSerializer, 403: OpenApiResponse(description="Permission refusée")},
    ),
    destroy=extend_schema(
        tags=["SubZone"],
        summary="Supprimer une sous-zone",
        responses={
            204: OpenApiResponse(description="Sous-zone supprimée"),
            403: OpenApiResponse(description="Permission refusée"),
        },
    ),
)
class SubZoneViewSet(viewsets.ModelViewSet):
    """Gestion des sous-zones — accès selon le rôle de l'utilisateur."""

    serializer_class = SubZoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return SubZone.objects.all()
        if hasattr(user, "country") and user.country:
            return SubZone.objects.filter(zone__country=user.country)
        raise PermissionDenied("You do not have permission to access these subzones.")

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_staff or (hasattr(user, "country") and user.country):
            serializer.save()
            return
        raise PermissionDenied("You cannot create a subzone.")

    def perform_update(self, serializer):
        user = self.request.user
        if user.is_staff or (hasattr(user, "country") and user.country):
            serializer.save()
            return
        raise PermissionDenied("You cannot update this subzone.")

    def perform_destroy(self, instance):
        user = self.request.user
        if user.is_staff or (hasattr(user, "country") and user.country):
            instance.delete()
            return
        raise PermissionDenied("You cannot delete this subzone.")