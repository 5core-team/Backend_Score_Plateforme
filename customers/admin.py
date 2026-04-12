from django.contrib import admin
from .models import Customer, ConsultationOTP, ConsultationSession, Debt, Repayment


# ─────────────────────────────────────────────
# CUSTOMER
# ─────────────────────────────────────────────

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display    = ['full_name', 'npi', 'email', 'phone_number', 'credit_score', 'zone', 'huissier']
    search_fields   = ['first_name', 'last_name', 'npi', 'email']
    list_filter     = ['zone', 'subZone', 'huissier']
    ordering        = ['last_name', 'first_name']
    readonly_fields = ['uuid', 'credit_score', 'created_at', 'updated_at']


# ─────────────────────────────────────────────
# CONSULTATION OTP
# ─────────────────────────────────────────────

@admin.register(ConsultationOTP)
class ConsultationOTPAdmin(admin.ModelAdmin):
    list_display    = ['customer', 'code', 'created_at', 'expiry_date', 'is_used']
    search_fields   = ['customer__first_name', 'customer__last_name', 'code']
    list_filter     = ['is_used']
    ordering        = ['-created_at']
    readonly_fields = ['created_at']


# ─────────────────────────────────────────────
# CONSULTATION SESSION
# ─────────────────────────────────────────────

@admin.register(ConsultationSession)
class ConsultationSessionAdmin(admin.ModelAdmin):
    list_display    = ['customer', 'created_by', 'created_at', 'expiry_date', 'is_active']
    search_fields   = ['customer__first_name', 'customer__last_name', 'created_by__email']
    list_filter     = ['is_active']
    ordering        = ['-created_at']
    readonly_fields = ['token', 'created_at']


# ─────────────────────────────────────────────
# DEBT
# ─────────────────────────────────────────────

@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display    = ['customer', 'creditor', 'amount', 'deadline_amount', 'periodicity', 'deadline', 'status', 'validation_status']  # ✅ verified → validation_status
    search_fields   = ['customer__first_name', 'customer__last_name', 'creditor__first_name']
    list_filter     = ['status', 'validation_status', 'periodicity']  # ✅ verified → validation_status
    ordering        = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'validation_token', 'validation_token_expiry']  # ✅ ajouté


# ─────────────────────────────────────────────
# REPAYMENT
# ─────────────────────────────────────────────

@admin.register(Repayment)
class RepaymentAdmin(admin.ModelAdmin):
    list_display    = ['debt', 'date', 'validation_status']  # ✅ validation_status ajouté
    search_fields   = ['debt__customer__first_name', 'debt__customer__last_name']
    list_filter     = ['validation_status']  # ✅ ajouté
    ordering        = ['-date']
    readonly_fields = ['validation_token', 'validation_token_expiry']  # ✅ ajouté