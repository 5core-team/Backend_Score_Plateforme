from django.urls import path
from .views import Login, NewCountry, CountrySubscribe, CountryData
from .views import CountryListView, CountrySubscriptions
from .views import HuissierCustomerListView, HuissierAlertsView, CustomerLoanDetailView
from .views import ZoneCustomerListView, SendEm

urlpatterns = [
    path("login/", Login.as_view()),
    path("email-test/", SendEm.as_view()),
    path("add-country/", NewCountry.as_view()),
    path("subscribe/", CountrySubscribe.as_view()),
    path("country/<str:country_name>/", CountryData.as_view()),
    path("country/<str:country_name>/subscriptions/", CountrySubscriptions.as_view()),
    path('countries/', CountryListView.as_view(), name='country-list'),
    path('huissier/customers/', HuissierCustomerListView.as_view()),
    path('huissier/customers/<str:customer_id>/', CustomerLoanDetailView.as_view()),
    path('huissier/alerts/', HuissierAlertsView.as_view()),
    path('huissier/zone/', ZoneCustomerListView.as_view())
]