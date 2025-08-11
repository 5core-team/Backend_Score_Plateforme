from django.urls import path
from .views import CreateCustomer, CustomersList, CustomerByNPI

urlpatterns = [
    path("new/", CreateCustomer.as_view()),
    path("list/", CustomersList.as_view()),
    path("by-npi/", CustomerByNPI.as_view()),
]