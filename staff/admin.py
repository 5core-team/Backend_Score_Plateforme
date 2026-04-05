from django.contrib import admin
from .models import FrontOffice, Huissier, FinancialAdvisor


# ─────────────────────────────────────────────
# FRONT OFFICE
# ─────────────────────────────────────────────

@admin.register(FrontOffice)
class FrontOfficeAdmin(admin.ModelAdmin):
    list_display  = ['user', 'zone', 'is_active']
    search_fields = ['user__email', 'user__username', 'zone__name']
    list_filter   = ['is_active', 'zone']
    ordering      = ['user__email']


# ─────────────────────────────────────────────
# HUISSIER
# ─────────────────────────────────────────────

@admin.register(Huissier)
class HuissierAdmin(admin.ModelAdmin):
    list_display  = ['user', 'zone', 'subZone', 'is_active']
    search_fields = ['user__email', 'user__username', 'zone__name', 'subZone__name']
    list_filter   = ['is_active', 'zone']
    ordering      = ['user__email']


# ─────────────────────────────────────────────
# FINANCIAL ADVISOR
# ─────────────────────────────────────────────

@admin.register(FinancialAdvisor)
class FinancialAdvisorAdmin(admin.ModelAdmin):
    list_display  = ['user', 'zone', 'subZone', 'is_active']
    search_fields = ['user__email', 'user__username', 'zone__name', 'subZone__name']
    list_filter   = ['is_active', 'zone']
    ordering      = ['user__email']