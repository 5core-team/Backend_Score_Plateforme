from django.urls import path
from .views import Login, ChangePassword

urlpatterns = [
    path('login/', Login.as_view()),
    path('change-password/', ChangePassword.as_view())
]
