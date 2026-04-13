from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import CountryViewSet, ZoneViewSet, SubZoneViewSet
from .subscription_views import (
    CreateSubscriptionView,
    RenewSubscriptionView,
    SubscriptionDetailView,
)

router = DefaultRouter()
router.register(r'countries', CountryViewSet, basename='country')
router.register(r'zones',     ZoneViewSet,    basename='zone')
router.register(r'subzones',  SubZoneViewSet, basename='subzone')

urlpatterns = router.urls + [
    path('countries/<int:country_id>/subscription/',        SubscriptionDetailView.as_view(),  name='subscription-detail'),
    path('countries/<int:country_id>/subscription/create/', CreateSubscriptionView.as_view(),  name='subscription-create'),
    path('countries/<int:country_id>/subscription/renew/',  RenewSubscriptionView.as_view(),   name='subscription-renew'),
]