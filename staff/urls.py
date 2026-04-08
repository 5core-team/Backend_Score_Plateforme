from rest_framework.routers import DefaultRouter
from .views import FrontOfficeViewSet, HuissierViewSet, FinancialAdvisorViewSet

router = DefaultRouter()
router.register(r'front-offices',      FrontOfficeViewSet,      basename='frontoffice')
router.register(r'huissiers',          HuissierViewSet,         basename='huissier')
router.register(r'financial-advisors', FinancialAdvisorViewSet, basename='financialadvisor')

urlpatterns = router.urls