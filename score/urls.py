
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

# ✅ Import Spectacular
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Tes apps
    path('auth/', include('accounts.urls')),
    path('geography/', include('geography.urls')),
    path('staff/', include('staff.urls')),
    path('customers/', include('customers.urls')),

    # ✅ Schema OpenAPI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # ✅ Swagger UI
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # ✅ Redoc
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# ✅ Gestion des fichiers media (OK chez toi)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)