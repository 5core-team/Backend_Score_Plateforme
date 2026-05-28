from django.urls import path
from .views import (
    Login,
    PasswordSetup,
    VerifyPasswordSetupCredentials,
    PasswordResetCode,
    VerifyValidationCode,
    ResetPassword,
    ProfileView,
    UpdateUsernameView,
    UpdatePhotoView,
    ChangePasswordRequestView,
    ConfirmPasswordChangeView,
    ContactFormView,
)

urlpatterns = [
    # 🔐 Authentification
    path('login/',                    Login.as_view(),                          name='login'),

    # 🔑 Setup du mot de passe initial (nouveau compte)
    path('verify-credentials/',       VerifyPasswordSetupCredentials.as_view(), name='verify-credentials'),
    path('password-setup/',           PasswordSetup.as_view(),                  name='password-setup'),

    # 🔄 Reset mot de passe (mot de passe oublié)
    path('reset-code/',               PasswordResetCode.as_view(),              name='reset-code'),
    path('verify-code/',              VerifyValidationCode.as_view(),           name='verify-code'),
    path('reset-password/',           ResetPassword.as_view(),                  name='reset-password'),

    # 👤 Profil
    path('profile/',                  ProfileView.as_view(),                    name='profile'),

    # ✅ Séparation username et photo
    path('profile/update-username/',  UpdateUsernameView.as_view(),             name='profile-update-username'),
    path('profile/upload-photo/',     UpdatePhotoView.as_view(),                name='profile-upload-photo'),

    # 🔒 Changement mot de passe via confirmation email
    path('profile/change-password/',  ChangePasswordRequestView.as_view(),      name='profile-change-password'),
    path('profile/confirm-password/', ConfirmPasswordChangeView.as_view(),      name='profile-confirm-password'),

    # 📬 Formulaire de contact public
    path('contact/',                  ContactFormView.as_view(),                name='contact'),
]