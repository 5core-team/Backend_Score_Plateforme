from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from .serializers import CountrySerializer
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Zone
from .serializers import ZoneSerializer
from .models import Country
from .serializers import CountrySerializer
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import SubZone
from .serializers import SubZoneSerializer

# class CountryViewSet(viewsets.ViewSet):
#     """
#     ViewSet to manage country (CRUD): for admin only
#     Dette techniques: Ajouter un signal pour envoyer un mail à l'utilisateur crée
#         Le mail contient un lien frontend (frontend.com/account/setup/?uid=...&token=...)
#     """
#     def create(self, request: Request):
#         serializer = CountrySerializer(request.data)
#         if (not serializer.is_valid()):
#             return Response(serializer.errors, status=400)
#         serializer.save()

#         return Response({
#             'msg': 'User successfully created.'
#         }, 201)




class CountryViewSet(viewsets.ViewSet):
    """
    ViewSet to manage country (CRUD): for admin only

    Dette techniques:
    - Ajouter un signal pour envoyer un mail à l'utilisateur créé
    - Le mail contient un lien frontend:
      frontend.com/account/setup/?uid=...&token=...
    """

    permission_classes = [IsAdminUser]

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

        return Response(
            {"msg": "Country successfully created."},
            status=status.HTTP_201_CREATED
        )

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


# class ZoneViewSet(viewsets.ModelViewSet):
#     """
#     Views to manage zone: Only for country user
#     """
#     pass




class ZoneViewSet(viewsets.ModelViewSet):
    """
    Views to manage zone: Only for country user
    """

    serializer_class = ZoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # فرض: user a un champ country
        return Zone.objects.filter(country=user.country)

    def perform_create(self, serializer):
        # On force la zone à appartenir au pays de l'utilisateur
        serializer.save(country=self.request.user.country)

# class SubZoneViewSet(viewsets.ModelViewSet):
#     """
#     Views to manage subZone: Only for country or appropriate front office user
#     """
#     pass




class SubZoneViewSet(viewsets.ModelViewSet):
    """
    Views to manage subZone: Only for country or appropriate front office user
    """

    serializer_class = SubZoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Front office (admin/staff) → accès à tout
        if user.is_staff:
            return SubZone.objects.all()

        # Country user → seulement ses subzones
        if hasattr(user, "country") and user.country:
            return SubZone.objects.filter(zone__country=user.country)

        # Sinon refus
        raise PermissionDenied("You do not have permission to access these subzones.")

    def perform_create(self, serializer):
        user = self.request.user

        if user.is_staff:
            serializer.save()
            return

        if hasattr(user, "country") and user.country:
            serializer.save()
            return

        raise PermissionDenied("You cannot create a subzone.")

    def perform_update(self, serializer):
        user = self.request.user

        if user.is_staff:
            serializer.save()
            return

        if hasattr(user, "country") and user.country:
            serializer.save()
            return

        raise PermissionDenied("You cannot update this subzone.")

    def perform_destroy(self, instance):
        user = self.request.user

        if user.is_staff:
            instance.delete()
            return

        if hasattr(user, "country") and user.country:
            instance.delete()
            return

        raise PermissionDenied("You cannot delete this subzone.")