from django.urls import path
from .views import (
    SuperAdminDashboardView,
    CountryDashboardView,
    FrontOfficeDashboardView,
    HuissierDashboardView,
    FinancialAdvisorDashboardView,
)

urlpatterns = [
    path('admin/',        SuperAdminDashboardView.as_view(),       name='dashboard-admin'),
    path('country/',      CountryDashboardView.as_view(),          name='dashboard-country'),
    path('front-office/', FrontOfficeDashboardView.as_view(),      name='dashboard-front-office'),
    path('huissier/',     HuissierDashboardView.as_view(),         name='dashboard-huissier'),
    path('conseiller/',   FinancialAdvisorDashboardView.as_view(), name='dashboard-conseiller'),
]