from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from users.views import (
    ChangePassword
    # ListeClients,
    # AjouterClient,
    # CreerUtilisateur,
    # ListerUtilisateursParRole,
    # UpdateDeleteUtilisateur,  # ✅ ajout de la vue
    # accueil
)



urlpatterns = [
    path('admin/', admin.site.urls),
    path("score/", include("users.urls")),
    path("country/", include("country.urls")),
    path("customer/", include("customer.urls")),
    path("change-password/", ChangePassword.as_view()),
    # path('login/', Login.as_view()),
#     path('clients/', ListeClients.as_view()),
#     path('ajouter-client/', AjouterClient.as_view()),
#     path('utilisateurs/', CreerUtilisateur.as_view()),
#     path('utilisateurs/<int:user_id>/', UpdateDeleteUtilisateur.as_view()),  # ✅ nouvelle route dynamique
#     path('utilisateurs-par-role/', ListerUtilisateursParRole.as_view()),
#     path('', accueil, name='accueil'),
 ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)