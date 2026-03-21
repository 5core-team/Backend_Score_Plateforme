from django.db import transaction
from rest_framework import viewsets

class CountryViewSet():
    """
    ViewSet to manage country (CRUD): for admin only
    """
    pass

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