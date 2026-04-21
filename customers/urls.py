from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    CustomerViewSet,
    DebtViewSet,
    RepaymentViewSet,
    DebtValidateView,
    DebtRejectView,
    RepaymentValidateView,
    RepaymentRejectView,
)

router = DefaultRouter()
router.register(r'customers',  CustomerViewSet,  basename='customer')
router.register(r'debts',      DebtViewSet,      basename='debt')
router.register(r'repayments', RepaymentViewSet, basename='repayment')

urlpatterns = router.urls + [
    # ── Dettes ────────────────────────────────────────────────────────
    path('debts/validate/', DebtValidateView.as_view(),  name='debt-validate'),
    path('debts/reject/',   DebtRejectView.as_view(),    name='debt-reject'),

    # ── Remboursements ────────────────────────────────────────────────
    path('repayments/validate/', RepaymentValidateView.as_view(), name='repayment-validate'),
    path('repayments/reject/',   RepaymentRejectView.as_view(),   name='repayment-reject'),
]