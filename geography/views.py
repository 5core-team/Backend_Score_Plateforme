from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from .serializers import CountrySerializer

class CountryViewSet(viewsets.ViewSet):
    """
    ViewSet to manage country (CRUD): for admin only
    """
    def create(self, request: Request):
        serializer = CountrySerializer(request.data)
        if (not serializer.is_valid()):
            return Response(serializer.errors, status=400)
        serializer.save()

        return Response({
            'msg': 'User successfully created.'
        }, 201)

class ZoneViewSet(viewsets.ModelViewSet):
    """
    Views to manage zone: Only for country user
    """
    pass

class SubZoneViewSet(viewsets.ModelViewSet):
    """
    Views to manage subZone: Only for country or appropriate front office user
    """
    pass