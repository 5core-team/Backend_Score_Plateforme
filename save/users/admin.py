from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import ScoreUser

@admin.register(ScoreUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role'),
        }),
    )
    # list_filter = ('role', 'is_staff', 'is_superuser')
    # fields = ('username', 'email', 'role', 'is_staff', 'is_active')

    # fieldsets = UserAdmin.fieldsets + (
    #     (None, {'fields': ('role',)}),
    # )
    # add_fieldsets = UserAdmin.add_fieldsets + (
    #     (None, {'fields': ('role',)}),
    # )



    # def has_add_permission(self, request):
    #     return hasattr(request.user, 'role') and request.user.role == 'admin'

    # def has_change_permission(self, request, obj=None):
    #     return hasattr(request.user, 'role') and request.user.role == 'admin'

    # def has_delete_permission(self, request, obj=None):
    #     return hasattr(request.user, 'role') and request.user.role == 'admin'


# @admin.register(Client)
# class ClientAdmin(admin.ModelAdmin):
#     list_display = ('prenom', 'nom', 'email', 'telephone', 'conseiller', 'date_creation')
#     list_filter = ('conseiller',)
#     search_fields = ('prenom', 'nom', 'email', 'telephone')

#     def has_add_permission(self, request):
#         return hasattr(request.user, 'role') and request.user.role == 'admin'

#     def has_change_permission(self, request, obj=None):
#         return hasattr(request.user, 'role') and request.user.role == 'admin'

#     def has_delete_permission(self, request, obj=None):
#         return hasattr(request.user, 'role') and request.user.role == 'admin'
