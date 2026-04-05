from django.urls import path
from .views import (
    Login,
    PasswordSetup,
    VerifyPasswordSetupCredentials,
    PasswordResetCode,
    VerifyValidationCode,
    ResetPassword,
    ChangePassword,   # ✅ ajouté
    ProfileView,      # ✅ ajouté
)

urlpatterns = [
    # 🔐 Authentification
    path('login/',               Login.as_view(),                          name='login'),

    # 🔑 Setup du mot de passe
    path('verify-credentials/',  VerifyPasswordSetupCredentials.as_view(), name='verify-credentials'),
    path('password-setup/',      PasswordSetup.as_view(),                  name='password-setup'),

    # 🔄 Reset mot de passe
    path('reset-code/',          PasswordResetCode.as_view(),              name='reset-code'),
    path('verify-code/',         VerifyValidationCode.as_view(),           name='verify-code'),
    path('reset-password/',      ResetPassword.as_view(),                  name='reset-password'),

    # 🔒 Changer mot de passe (authentifié)
    path('change-password/',     ChangePassword.as_view(),                 name='change-password'),

    # 👤 Profil
    path('profile/',             ProfileView.as_view(),                    name='profile'),
]