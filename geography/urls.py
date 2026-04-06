from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import CountryViewSet, ZoneViewSet, SubZoneViewSet

router = DefaultRouter()
router.register(r'countries', CountryViewSet, basename='country')
router.register(r'zones',     ZoneViewSet,    basename='zone')
router.register(r'subzones',  SubZoneViewSet, basename='subzone')

urlpatterns = router.urls