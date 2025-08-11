from rest_framework.permissions import BasePermission

class IsScoreAdmin(BasePermission):
    message = "Only admin allowed"

    def has_permission(self, request, view):
        return request.user.role == "admin"

class IsCountry(BasePermission):
    message = "Only country representative allowed"
    def has_permission(self, request, view):
        return request.user.role == "country"

class IsFrontOffice(BasePermission):
    message = "Only front office allowed"

    def has_permission(self, request, view):
        return request.user.role == "front office"

class IsHuissier(BasePermission):
    message = "Only huissier allowed"

    def has_permission(self, request, view):
        return request.user.role == "huissier"

class IsFinancial(BasePermission):
    message = "Only financial allowed"

    def has_permission(self, request, view):
        return request.user.role == "conseiller"    

class IsPasswordChanged(BasePermission):
    message = "Need to update password firstly"
    def has_permission(self, request, view):
        return request.user.password_changed

# class HasValidSubscription(BasePermission):
#     message = "No valid subscription available"

#     def has_permission(self, request, view):
        
