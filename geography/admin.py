from django.contrib import admin
from .models import Country, Zone, SubZone


# ─────────────────────────────────────────────
# COUNTRY
# ─────────────────────────────────────────────

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'iso_code', 'manager', 'created_at']
    search_fields = ['name', 'iso_code', 'manager__email']
    list_filter   = ['created_at']
    ordering      = ['name']
    readonly_fields = ['created_at', 'updated_at']


# ─────────────────────────────────────────────
# ZONE
# ─────────────────────────────────────────────

@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display  = ['name', 'country']
    search_fields = ['name', 'country__name']
    list_filter   = ['country']
    ordering      = ['country', 'name']


# ─────────────────────────────────────────────
# SUBZONE
# ─────────────────────────────────────────────

@admin.register(SubZone)
class SubZoneAdmin(admin.ModelAdmin):
    list_display  = ['name', 'zone', 'get_country']
    search_fields = ['name', 'zone__name', 'zone__country__name']
    list_filter   = ['zone__country', 'zone']
    ordering      = ['zone', 'name']

    def get_country(self, obj):
        return obj.zone.country.name
    get_country.short_description = 'Pays'