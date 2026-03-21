from django.contrib import admin
from .models import Country, Subscription, FrontOffice, AvailableZone, Huissier, Financial
# Register your models here.

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    pass

admin.site.register(AvailableZone)
