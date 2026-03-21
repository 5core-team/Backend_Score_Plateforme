from django.contrib import admin
from .models import Customer, Loan
# Register your models here.

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    pass
admin.site.register(Loan)