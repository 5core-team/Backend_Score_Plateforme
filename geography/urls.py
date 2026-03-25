from django.urls import path
from .views import CountryViewSet

urlpatterns = [
    path('add-country/', CountryViewSet.as_view({'post', 'create'})),
]
