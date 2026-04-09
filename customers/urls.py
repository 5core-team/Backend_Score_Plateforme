from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, DebtViewSet, RepaymentViewSet

router = DefaultRouter()
router.register(r'customers',   CustomerViewSet,   basename='customer')
router.register(r'debts',       DebtViewSet,       basename='debt')
router.register(r'repayments',  RepaymentViewSet,  basename='repayment')

urlpatterns = router.urls