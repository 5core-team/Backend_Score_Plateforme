from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import ScoreUser, AccountCredentials


@admin.register(ScoreUser)
class ScoreUserAdmin(UserAdmin):
    model = ScoreUser

    list_display  = ['email', 'username', 'role', 'is_active', 'is_staff']
    list_filter   = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'username']
    ordering      = ['email']

    fieldsets = (
        (None,           {'fields': ('email', 'password')}),
        ('Informations', {'fields': ('username', 'role', 'photo', 'password_changed')}),
        ('Permissions',  {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'role', 'is_staff', 'is_active'),
        }),
    )


@admin.register(AccountCredentials)
class AccountCredentialsAdmin(admin.ModelAdmin):
    list_display  = ['user', 'token', 'expiry_date', 'created_at']
    search_fields = ['user__email']