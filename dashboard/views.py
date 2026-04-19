from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count

from geography.models import Country, Zone
from staff.models import FrontOffice, Huissier, FinancialAdvisor
from customers.models import Customer, Debt, Repayment, ConsultationSession, ConsultationOTP

from drf_spectacular.utils import extend_schema
from .permissions import IsSuperAdmin


# ─────────────────────────────────────────────
# DASHBOARD SUPER ADMIN
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Dashboard"],
    summary="Dashboard Super Admin",
    description="Retourne toutes les statistiques globales de la plateforme. Réservé au super admin.",
    responses=None,
)
class SuperAdminDashboardView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        now = timezone.now()

        countries_qs      = Country.objects.all()
        total_countries   = countries_qs.count()
        active_countries  = countries_qs.filter(
            subscription__expires_in__gt=now,
            subscription__is_blocked=False
        ).distinct().count()
        expired_countries = total_countries - active_countries

        countries_detail = countries_qs.values('id', 'name', 'iso_code').annotate(
            front_office_count=Count('zones__frontoffice', distinct=True),
            customer_count=Count('zones__customers', distinct=True),
        )

        total_front_offices  = FrontOffice.objects.count()
        active_front_offices = FrontOffice.objects.filter(is_active=True).count()

        total_huissiers  = Huissier.objects.count()
        active_huissiers = Huissier.objects.filter(is_active=True).count()

        total_advisors  = FinancialAdvisor.objects.count()
        active_advisors = FinancialAdvisor.objects.filter(is_active=True).count()

        total_customers = Customer.objects.count()

        customers_by_country = (
            Customer.objects
            .values('zone__country__name', 'zone__country__id')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        debts_qs            = Debt.objects.all()
        total_debts         = debts_qs.count()
        pending_debts       = debts_qs.filter(status='pending').count()
        done_debts          = debts_qs.filter(status='done').count()
        verified_debts      = debts_qs.filter(validation_status='validated').count()          # ✅
        unverified_debts    = debts_qs.filter(validation_status__in=['pending', 'rejected']).count()  # ✅
        overdue_debts       = debts_qs.filter(status='pending', deadline__lt=now.date()).count()
        total_debt_amount   = debts_qs.aggregate(total=Sum('amount'))['total'] or 0
        pending_debt_amount = debts_qs.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

        total_repayments = Repayment.objects.count()

        active_sessions = ConsultationSession.objects.filter(
            is_active=True,
            expiry_date__gt=now
        ).count()

        recent_otps = ConsultationOTP.objects.filter(
            created_at__gte=now - timezone.timedelta(hours=24)
        ).count()

        return Response({
            "countries": {
                "total":   total_countries,
                "active":  active_countries,
                "expired": expired_countries,
                "detail":  list(countries_detail),
            },
            "staff": {
                "front_offices":      {"total": total_front_offices,  "active": active_front_offices},
                "huissiers":          {"total": total_huissiers,       "active": active_huissiers},
                "financial_advisors": {"total": total_advisors,        "active": active_advisors},
            },
            "customers": {
                "total":      total_customers,
                "by_country": list(customers_by_country),
            },
            "debts": {
                "total":          total_debts,
                "pending":        pending_debts,
                "done":           done_debts,
                "overdue":        overdue_debts,
                "verified":       verified_debts,
                "unverified":     unverified_debts,
                "total_amount":   float(total_debt_amount),
                "pending_amount": float(pending_debt_amount),
            },
            "repayments": {"total": total_repayments},
            "activity": {
                "active_sessions": active_sessions,
                "otps_last_24h":   recent_otps,
            },
        })


# ─────────────────────────────────────────────
# DASHBOARD REPRÉSENTANT PAYS
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Dashboard"],
    summary="Dashboard Représentant Pays",
    description="Retourne les statistiques du pays géré par le représentant connecté.",
    responses=None,
)
class CountryDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        if request.user.role != 'country':
            return Response(
                {"error": "Accès réservé au représentant pays."},
                status=403
            )

        try:
            country = Country.objects.get(manager=request.user)
        except Country.DoesNotExist:
            return Response(
                {"error": "Aucun pays associé à votre compte."},
                status=404
            )

        subscription      = getattr(country, 'subscription', None)
        subscription_info = {
            "is_active":  subscription.is_active() if subscription else False,
            "expires_in": subscription.expires_in if subscription else None,
        }

        zones        = Zone.objects.filter(country=country)
        zones_detail = zones.values('id', 'name').annotate(
            customer_count=Count('customers', distinct=True),
            front_office_count=Count('frontoffice', distinct=True),
        )

        total_front_offices  = FrontOffice.objects.filter(zone__country=country).count()
        active_front_offices = FrontOffice.objects.filter(zone__country=country, is_active=True).count()

        total_huissiers  = Huissier.objects.filter(zone__country=country).count()
        active_huissiers = Huissier.objects.filter(zone__country=country, is_active=True).count()

        total_advisors  = FinancialAdvisor.objects.filter(zone__country=country).count()
        active_advisors = FinancialAdvisor.objects.filter(zone__country=country, is_active=True).count()

        total_customers = Customer.objects.filter(zone__country=country).count()

        customers_by_zone = (
            Customer.objects
            .filter(zone__country=country)
            .values('zone__name', 'zone__id')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        debts_qs = Debt.objects.filter(customer__zone__country=country)

        total_debts         = debts_qs.count()
        pending_debts       = debts_qs.filter(status='pending').count()
        done_debts          = debts_qs.filter(status='done').count()
        overdue_debts       = debts_qs.filter(status='pending', deadline__lt=now.date()).count()
        verified_debts      = debts_qs.filter(validation_status='validated').count()                  # ✅
        unverified_debts    = debts_qs.filter(validation_status__in=['pending', 'rejected']).count()  # ✅
        total_debt_amount   = debts_qs.aggregate(total=Sum('amount'))['total'] or 0
        pending_debt_amount = debts_qs.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

        total_repayments = Repayment.objects.filter(
            debt__customer__zone__country=country
        ).count()

        active_sessions = ConsultationSession.objects.filter(
            customer__zone__country=country,
            is_active=True,
            expiry_date__gt=now
        ).count()

        recent_otps = ConsultationOTP.objects.filter(
            customer__zone__country=country,
            created_at__gte=now - timezone.timedelta(hours=24)
        ).count()

        return Response({
            "country": {
                "id":           country.id,
                "name":         country.name,
                "iso_code":     country.iso_code,
                "subscription": subscription_info,
            },
            "zones": {
                "total":  zones.count(),
                "detail": list(zones_detail),
            },
            "staff": {
                "front_offices":      {"total": total_front_offices,  "active": active_front_offices},
                "huissiers":          {"total": total_huissiers,       "active": active_huissiers},
                "financial_advisors": {"total": total_advisors,        "active": active_advisors},
            },
            "customers": {
                "total":   total_customers,
                "by_zone": list(customers_by_zone),
            },
            "debts": {
                "total":          total_debts,
                "pending":        pending_debts,
                "done":           done_debts,
                "overdue":        overdue_debts,
                "verified":       verified_debts,
                "unverified":     unverified_debts,
                "total_amount":   float(total_debt_amount),
                "pending_amount": float(pending_debt_amount),
            },
            "repayments": {"total": total_repayments},
            "activity": {
                "active_sessions": active_sessions,
                "otps_last_24h":   recent_otps,
            },
        })


# ─────────────────────────────────────────────
# DASHBOARD FRONT OFFICE
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Dashboard"],
    summary="Dashboard Front Office",
    description="Retourne les statistiques de la zone gérée par le front office connecté.",
    responses=None,
)
class FrontOfficeDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        if request.user.role != 'front office':
            return Response(
                {"error": "Accès réservé au front office."},
                status=403
            )

        try:
            front_office = FrontOffice.objects.get(user=request.user)
        except FrontOffice.DoesNotExist:
            return Response(
                {"error": "Aucun front office associé à votre compte."},
                status=404
            )

        zone = front_office.zone

        from geography.models import SubZone
        subzones        = SubZone.objects.filter(zone=zone)
        subzones_detail = subzones.values('id', 'name').annotate(
            customer_count=Count('customers', distinct=True),
        )

        total_huissiers  = Huissier.objects.filter(zone=zone).count()
        active_huissiers = Huissier.objects.filter(zone=zone, is_active=True).count()

        total_advisors  = FinancialAdvisor.objects.filter(zone=zone).count()
        active_advisors = FinancialAdvisor.objects.filter(zone=zone, is_active=True).count()

        total_customers      = Customer.objects.filter(zone=zone).count()
        customers_by_subzone = (
            Customer.objects
            .filter(zone=zone)
            .values('subZone__name', 'subZone__id')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        debts_qs            = Debt.objects.filter(customer__zone=zone)
        total_debts         = debts_qs.count()
        pending_debts       = debts_qs.filter(status='pending').count()
        done_debts          = debts_qs.filter(status='done').count()
        overdue_debts       = debts_qs.filter(status='pending', deadline__lt=now.date()).count()
        verified_debts      = debts_qs.filter(validation_status='validated').count()                  # ✅
        unverified_debts    = debts_qs.filter(validation_status__in=['pending', 'rejected']).count()  # ✅
        total_debt_amount   = debts_qs.aggregate(total=Sum('amount'))['total'] or 0
        pending_debt_amount = debts_qs.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

        total_repayments = Repayment.objects.filter(debt__customer__zone=zone).count()

        active_sessions = ConsultationSession.objects.filter(
            customer__zone=zone,
            is_active=True,
            expiry_date__gt=now
        ).count()

        recent_otps = ConsultationOTP.objects.filter(
            customer__zone=zone,
            created_at__gte=now - timezone.timedelta(hours=24)
        ).count()

        return Response({
            "front_office": {
                "id":   front_office.id,
                "name": front_office.name,
                "zone": {
                    "id":      zone.id,
                    "name":    zone.name,
                    "country": zone.country.name,
                },
            },
            "subzones": {
                "total":  subzones.count(),
                "detail": list(subzones_detail),
            },
            "staff": {
                "huissiers":          {"total": total_huissiers,  "active": active_huissiers},
                "financial_advisors": {"total": total_advisors,   "active": active_advisors},
            },
            "customers": {
                "total":      total_customers,
                "by_subzone": list(customers_by_subzone),
            },
            "debts": {
                "total":          total_debts,
                "pending":        pending_debts,
                "done":           done_debts,
                "overdue":        overdue_debts,
                "verified":       verified_debts,
                "unverified":     unverified_debts,
                "total_amount":   float(total_debt_amount),
                "pending_amount": float(pending_debt_amount),
            },
            "repayments": {"total": total_repayments},
            "activity": {
                "active_sessions": active_sessions,
                "otps_last_24h":   recent_otps,
            },
        })


# ─────────────────────────────────────────────
# DASHBOARD HUISSIER
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Dashboard"],
    summary="Dashboard Huissier",
    description="Retourne les statistiques de l'huissier connecté.",
    responses=None,
)
class HuissierDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        if request.user.role != 'huissier':
            return Response(
                {"error": "Accès réservé aux huissiers."},
                status=403
            )

        try:
            huissier = Huissier.objects.get(user=request.user)
        except Huissier.DoesNotExist:
            return Response(
                {"error": "Aucun profil huissier associé à votre compte."},
                status=404
            )

        total_customers = Customer.objects.filter(huissier=huissier).count()

        debts_qs        = Debt.objects.filter(customer__huissier=huissier)
        total_debts     = debts_qs.count()
        verified_debts  = debts_qs.filter(validation_status='validated').count()  # ✅
        taux_de_reponse = round((verified_debts / total_debts * 100), 1) if total_debts > 0 else 0

        total_consultations = ConsultationSession.objects.filter(
            created_by=request.user
        ).count()

        consulted_customer_ids = (
            ConsultationSession.objects
            .filter(created_by=request.user)
            .values_list('customer_id', flat=True)
            .distinct()
        )

        dettes_suivies_qs      = Debt.objects.filter(customer__id__in=consulted_customer_ids)
        total_dettes_suivies   = dettes_suivies_qs.count()
        pending_dettes_suivies = dettes_suivies_qs.filter(status='pending').count()
        done_dettes_suivies    = dettes_suivies_qs.filter(status='done').count()
        overdue_dettes_suivies = dettes_suivies_qs.filter(
            status='pending', deadline__lt=now.date()
        ).count()
        total_amount_suivies   = dettes_suivies_qs.aggregate(total=Sum('amount'))['total'] or 0

        total_remboursements_suivis = Repayment.objects.filter(
            debt__customer__id__in=consulted_customer_ids
        ).count()

        derniers_otps = (
            ConsultationOTP.objects
            .filter(customer__huissier=huissier)
            .order_by('-created_at')[:10]
        )

        consultations_detail = []
        for otp in derniers_otps:
            if otp.is_used:
                statut = 'validé'
            elif timezone.now() > otp.expiry_date:
                statut = 'expiré'
            else:
                statut = 'en attente'

            consultations_detail.append({
                "id":     f"#REQ-{otp.id:05d}",
                "date":   otp.created_at,
                "statut": statut,
                "otp_id": otp.id,
                "session_token": (
                    str(
                        ConsultationSession.objects
                        .filter(customer=otp.customer, created_by=request.user)
                        .order_by('-created_at')
                        .values_list('token', flat=True)
                        .first()
                    ) if otp.is_used else None
                ),
            })

        return Response({
            "huissier": {
                "id":       huissier.id,
                "email":    request.user.email,
                "username": request.user.username,
                "zone":     huissier.zone.name if huissier.zone else None,
                "subzone":  huissier.subZone.name if huissier.subZone else None,
            },
            "stats": {
                "dossiers_crees":      total_customers,
                "taux_de_reponse":     taux_de_reponse,
                "total_consultations": total_consultations,
                "dettes_suivies": {
                    "total":        total_dettes_suivies,
                    "pending":      pending_dettes_suivies,
                    "done":         done_dettes_suivies,
                    "overdue":      overdue_dettes_suivies,
                    "total_amount": float(total_amount_suivies),
                },
                "remboursements_suivis": {
                    "total": total_remboursements_suivis,
                },
            },
            "dernieres_consultations": consultations_detail,
        })


# ─────────────────────────────────────────────
# DASHBOARD CONSEILLER FINANCIER
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Dashboard"],
    summary="Dashboard Conseiller Financier",
    description="Retourne les statistiques du conseiller financier connecté.",
    responses=None,
)
class FinancialAdvisorDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        if request.user.role != 'conseiller':
            return Response(
                {"error": "Accès réservé aux conseillers financiers."},
                status=403
            )

        try:
            advisor = FinancialAdvisor.objects.get(user=request.user)
        except FinancialAdvisor.DoesNotExist:
            return Response(
                {"error": "Aucun profil conseiller associé à votre compte."},
                status=404
            )

        total_consultations = ConsultationSession.objects.filter(
            created_by=request.user
        ).count()

        otps_qs         = ConsultationOTP.objects.filter(customer__zone=advisor.zone)
        total_otps      = otps_qs.count()
        validated_otps  = otps_qs.filter(is_used=True).count()
        taux_de_reponse = round((validated_otps / total_otps * 100), 1) if total_otps > 0 else 0

        derniers_otps = (
            ConsultationOTP.objects
            .filter(customer__zone=advisor.zone)
            .order_by('-created_at')[:10]
        )

        consultations_detail = []
        for otp in derniers_otps:
            if otp.is_used:
                statut = 'validé'
            elif timezone.now() > otp.expiry_date:
                statut = 'expiré'
            else:
                statut = 'en attente'

            consultations_detail.append({
                "id":     f"#REQ-{otp.id:05d}",
                "date":   otp.created_at,
                "statut": statut,
                "otp_id": otp.id,
                "session_token": (
                    str(
                        ConsultationSession.objects
                        .filter(customer=otp.customer, created_by=request.user)
                        .order_by('-created_at')
                        .values_list('token', flat=True)
                        .first()
                    ) if otp.is_used else None
                ),
            })

        return Response({
            "conseiller": {
                "id":       advisor.id,
                "email":    request.user.email,
                "username": request.user.username,
                "zone":     advisor.zone.name if advisor.zone else None,
                "subzone":  advisor.subZone.name if advisor.subZone else None,
            },
            "stats": {
                "total_consultations": total_consultations,
                "taux_de_reponse":     taux_de_reponse,
            },
            "dernieres_consultations": consultations_detail,
        })