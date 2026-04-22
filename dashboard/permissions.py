from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """Réservé au super admin uniquement."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser


class IsCountry(BasePermission):
    """Réservé au représentant pays uniquement."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'country'


class IsFrontOffice(BasePermission):
    """Réservé au front office uniquement."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'front office'


class IsHuissier(BasePermission):
    """Réservé à l'huissier uniquement."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'huissier'


class IsFinancialAdvisor(BasePermission):
    """Réservé au conseiller financier uniquement."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'conseiller'