from rest_framework.permissions import BasePermission

class IsSuperAdmin(BasePermission):
    """Réservé au super admin uniquement."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser