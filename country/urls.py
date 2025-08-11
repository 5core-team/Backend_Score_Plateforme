from django.urls import path
from .views import CreateFrontOffice, AddZone, RemoveZone
from .views import CreateHuissier, Zones
from .views import CreateConseillerFinancier, ConsultCustomerAccount, CheckConsultationCode
from .views import RegisterLoan, RegisterLoanCode

urlpatterns = [
    path("create-front-office/", CreateFrontOffice.as_view()),
    path("add-zone/", AddZone.as_view()),
    path("remove-zone/", RemoveZone.as_view()),
    path("get-zones/", Zones.as_view()),
    path("create-huissier/", CreateHuissier.as_view(), name="create_huissier"),
    path("create-conseiller/", CreateConseillerFinancier.as_view(), name="create_conseiller"),
    path("consultation-request/", ConsultCustomerAccount.as_view()),
    path("customer-data/", CheckConsultationCode.as_view()),
    path("get-loan-code/", RegisterLoanCode.as_view()),
    path("register-loan/", RegisterLoan.as_view())
]
