from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, BasePermission, SAFE_METHODS
from rest_framework.response import Response
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta

from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiResponse, OpenApiParameter

from .models import Customer, ConsultationOTP, ConsultationSession, Debt, Repayment
from .serializers import (
    CustomerSerializer,
    CustomerSearchSerializer,
    ConsultationOTPRequestSerializer,
    ConsultationOTPVerifySerializer,
    ConsultationSessionSerializer,
    DebtSerializer,
    RepaymentSerializer,
)


# ─────────────────────────────────────────────
# PERMISSIONS
# ─────────────────────────────────────────────

class IsHuissier(BasePermission):
    """Huissier → toutes les actions."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'huissier'


class IsHuissierOrAdvisor(BasePermission):
    """
    Huissier → toutes les actions.
    Conseiller → lecture uniquement.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.role == 'huissier':
            return True
        if user.role == 'conseiller' and request.method in SAFE_METHODS:
            return True
        return False


# ─────────────────────────────────────────────
# HELPER — Vérification session de consultation
# ─────────────────────────────────────────────

def get_valid_session(session_token, customer_id):
    try:
        session = ConsultationSession.objects.get(
            token=session_token,
            customer_id=customer_id,
            is_active=True,
        )
        if not session.is_valid():
            return None, "Session expirée."
        return session, None
    except ConsultationSession.DoesNotExist:
        return None, "Session invalide."


# ─────────────────────────────────────────────
# CUSTOMER VIEWSET
# ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=["Customers"],
        summary="Lister les clients",
        responses={200: CustomerSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Customers"],
        summary="Récupérer un client",
        responses={200: CustomerSerializer},
    ),
    create=extend_schema(
        tags=["Customers"],
        summary="Créer un client",
        description="Réservé à l'huissier uniquement.",
        request=CustomerSerializer,
        responses={
            201: CustomerSerializer,
            400: OpenApiResponse(description="Données invalides"),
            403: OpenApiResponse(description="Permission refusée"),
        },
    ),
    update=extend_schema(
        tags=["Customers"],
        summary="Modifier un client",
        description="Réservé à l'huissier uniquement.",
        request=CustomerSerializer,
        responses={200: CustomerSerializer},
    ),
    partial_update=extend_schema(
        tags=["Customers"],
        summary="Modifier partiellement un client",
        request=CustomerSerializer,
        responses={200: CustomerSerializer},
    ),
    destroy=extend_schema(
        tags=["Customers"],
        summary="Supprimer un client",
        description="Réservé à l'huissier uniquement.",
        responses={204: OpenApiResponse(description="Client supprimé")},
    ),
)
class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class   = CustomerSerializer
    lookup_value_regex = r'\d+'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHuissier()]
        return [IsHuissierOrAdvisor()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Customer.objects.all()
        if user.role in ['huissier', 'conseiller']:
            return Customer.objects.all()
        return Customer.objects.none()

    @extend_schema(
        tags=["Customers"],
        summary="Rechercher un client",
        description="Recherche par nom ou NPI avant de demander l'OTP.",
        parameters=[
            OpenApiParameter(name='q', type=str, location=OpenApiParameter.QUERY, required=True),
        ],
        responses={200: CustomerSearchSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], url_path='search', permission_classes=[IsHuissierOrAdvisor])
    def search(self, request):
        query = request.query_params.get('q', '').strip()

        if not query:
            return Response(
                {"error": "Paramètre 'q' requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        customers = Customer.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)  |
            Q(npi__icontains=query)
        )

        serializer = CustomerSearchSerializer(customers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Customers"],
        summary="Demander un code OTP de consultation",
        description="Envoie un code OTP par mail au client pour autoriser la consultation.",
        request=ConsultationOTPRequestSerializer,
        responses={
            200: OpenApiResponse(description="OTP envoyé au client"),
            400: OpenApiResponse(description="Délai non respecté ou client introuvable"),
        },
    )
    @action(detail=False, methods=['post'], url_path='request-otp', permission_classes=[IsHuissierOrAdvisor])
    def request_otp(self, request):
        serializer = ConsultationOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            serializer.send_otp()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"msg": "Code OTP envoyé au client par mail."},
            status=status.HTTP_200_OK
        )

    @extend_schema(
        tags=["Customers"],
        summary="Vérifier le code OTP et ouvrir une session de consultation",
        description="Valide le code OTP et retourne un token de session valable 30 minutes.",
        request=ConsultationOTPVerifySerializer,
        responses={
            200: OpenApiResponse(description="Session ouverte — token retourné"),
            400: OpenApiResponse(description="Code invalide ou expiré"),
        },
    )
    @action(detail=False, methods=['post'], url_path='verify-otp', permission_classes=[IsHuissierOrAdvisor])
    def verify_otp(self, request):
        serializer = ConsultationOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer = serializer.validated_data['customer']
        otp      = serializer.validated_data['otp']

        otp.is_used = True
        otp.save()

        expiry_mins = getattr(settings, "CONSULTATION_SESSION_EXPIRY_MINUTES", 30)
        session = ConsultationSession.objects.create(
            customer=customer,
            created_by=request.user,
            expiry_date=timezone.now() + timedelta(minutes=expiry_mins),
        )

        return Response(
            {
                "msg":           "Session de consultation ouverte.",
                "session_token": str(session.token),
                "customer":      CustomerSerializer(customer).data,
                "expires_in":    expiry_mins * 60,
            },
            status=status.HTTP_200_OK
        )


# ─────────────────────────────────────────────
# DEBT VIEWSET
# ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=["Customers - Dettes"],
        summary="Lister les dettes",
        description="Huissier + Conseiller → toutes les dettes (lecture seule pour conseiller).",
        responses={200: DebtSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Customers - Dettes"],
        summary="Récupérer une dette",
        responses={200: DebtSerializer},
    ),
    create=extend_schema(
        tags=["Customers - Dettes"],
        summary="Créer une dette",
        description="Réservé à l'huissier uniquement. Nécessite un session_token valide.",
        request=DebtSerializer,
        responses={
            201: DebtSerializer,
            400: OpenApiResponse(description="Session invalide ou expirée"),
            403: OpenApiResponse(description="Permission refusée"),
        },
    ),
    update=extend_schema(
        tags=["Customers - Dettes"],
        summary="Modifier une dette",
        description="Réservé à l'huissier uniquement. Impossible si déjà validée par le client.",
        request=DebtSerializer,
        responses={200: DebtSerializer},
    ),
    partial_update=extend_schema(
        tags=["Customers - Dettes"],
        summary="Modifier partiellement une dette",
        description="Impossible si déjà validée par le client.",
        request=DebtSerializer,
        responses={200: DebtSerializer},
    ),
)
class DebtViewSet(viewsets.ModelViewSet):
    serializer_class   = DebtSerializer
    lookup_value_regex = r'\d+'

    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'toggle_monitoring']:
            return [IsHuissier()]
        return [IsHuissierOrAdvisor()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Debt.objects.all()
        if user.role in ['huissier', 'conseiller']:
            return Debt.objects.all()
        return Debt.objects.none()

    def create(self, request, *args, **kwargs):
        session_token = request.data.get('session_token')
        customer_id   = request.data.get('customer')

        if not session_token:
            return Response(
                {"error": "session_token requis pour ajouter une dette."},
                status=status.HTTP_400_BAD_REQUEST
            )

        session, error = get_valid_session(session_token, customer_id)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        debt = self.get_object()
        if not debt.is_editable():
            return Response(
                {"error": "Cette dette a déjà été validée par le client et ne peut plus être modifiée."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        debt = self.get_object()
        if not debt.is_editable():
            return Response(
                {"error": "Cette dette a déjà été validée par le client et ne peut plus être modifiée."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().partial_update(request, *args, **kwargs)

    # ✅ toggle_monitoring DANS la classe DebtViewSet
    @extend_schema(
        tags=["Customers - Dettes"],
        summary="Activer/désactiver le suivi d'une dette",
        description="L'huissier active ou désactive le suivi d'une dette. Uniquement pour les dettes validées.",
        request=None,
        responses=None,
    )
    @action(detail=True, methods=['post'], url_path='toggle-monitoring', permission_classes=[IsHuissier])
    def toggle_monitoring(self, request, pk=None):
        debt = self.get_object()

        if debt.validation_status != 'validated':
            return Response(
                {"error": "Vous ne pouvez surveiller que les dettes validées par le client."},
                status=status.HTTP_400_BAD_REQUEST
            )

        debt.is_monitored = not debt.is_monitored
        debt.save(update_fields=['is_monitored'])

        return Response(
            {
                "message":      f"Suivi {'activé' if debt.is_monitored else 'désactivé'} avec succès.",
                "is_monitored": debt.is_monitored,
            },
            status=status.HTTP_200_OK
        )


# ─────────────────────────────────────────────
# REPAYMENT VIEWSET
# ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=["Customers - Remboursements"],
        summary="Lister les remboursements",
        responses={200: RepaymentSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Customers - Remboursements"],
        summary="Récupérer un remboursement",
        responses={200: RepaymentSerializer},
    ),
    create=extend_schema(
        tags=["Customers - Remboursements"],
        summary="Créer un remboursement",
        description="Réservé à l'huissier uniquement. Nécessite un session_token valide.",
        request=RepaymentSerializer,
        responses={
            201: RepaymentSerializer,
            400: OpenApiResponse(description="Session invalide ou expirée"),
            403: OpenApiResponse(description="Permission refusée"),
        },
    ),
    update=extend_schema(
        tags=["Customers - Remboursements"],
        summary="Modifier un remboursement",
        description="Réservé à l'huissier uniquement. Impossible si déjà validé par le client.",
        request=RepaymentSerializer,
        responses={200: RepaymentSerializer},
    ),
    partial_update=extend_schema(
        tags=["Customers - Remboursements"],
        summary="Modifier partiellement un remboursement",
        description="Impossible si déjà validé par le client.",
        request=RepaymentSerializer,
        responses={200: RepaymentSerializer},
    ),
)
class RepaymentViewSet(viewsets.ModelViewSet):
    serializer_class   = RepaymentSerializer
    lookup_value_regex = r'\d+'

    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [IsHuissier()]
        return [IsHuissierOrAdvisor()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Repayment.objects.all()
        if user.role in ['huissier', 'conseiller']:
            return Repayment.objects.all()
        return Repayment.objects.none()

    def create(self, request, *args, **kwargs):
        session_token = request.data.get('session_token')
        debt_id       = request.data.get('debt')

        if not session_token:
            return Response(
                {"error": "session_token requis pour ajouter un remboursement."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            debt        = Debt.objects.get(id=debt_id)
            customer_id = debt.customer.id
        except Exception:
            return Response(
                {"error": "Dette introuvable."},
                status=status.HTTP_400_BAD_REQUEST
            )

        session, error = get_valid_session(session_token, customer_id)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        repayment = self.get_object()
        if not repayment.is_editable():
            return Response(
                {"error": "Ce remboursement a déjà été validé par le client et ne peut plus être modifié."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        repayment = self.get_object()
        if not repayment.is_editable():
            return Response(
                {"error": "Ce remboursement a déjà été validé par le client et ne peut plus être modifié."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().partial_update(request, *args, **kwargs)


# ─────────────────────────────────────────────
# VALIDATION DETTE PAR LIEN UNIQUE
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Customers - Dettes"],
    summary="Envoyer le lien de validation d'une dette",
    description="Envoie un lien unique au client pour valider ou refuser la dette.",
    request=None,
    responses=None,
)
class DebtSendValidationView(APIView):
    permission_classes = [IsHuissier]

    def post(self, request, pk):
        try:
            debt = Debt.objects.get(pk=pk)
        except Debt.DoesNotExist:
            return Response(
                {"error": "Dette introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not debt.is_editable():
            return Response(
                {"error": "Cette dette a déjà été validée par le client."},
                status=status.HTTP_400_BAD_REQUEST
            )

        token = debt.generate_validation_token()

        base_url     = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        validate_url = f"{base_url}/debts/validate/?token={token}"
        reject_url   = f"{base_url}/debts/reject/?token={token}"

        send_mail(
            subject        = "[SCORE] Confirmation d'enregistrement de dette",
            message        = (
                f"Bonjour {debt.customer.full_name},\n\n"
                f"Une dette a été enregistrée à votre nom :\n"
                f"- Montant       : {debt.amount}\n"
                f"- Échéance      : {debt.deadline}\n"
                f"- Périodicité   : {debt.periodicity}\n\n"
                f"Pour VALIDER cette dette, cliquez ici :\n{validate_url}\n\n"
                f"Pour REFUSER cette dette, cliquez ici :\n{reject_url}\n\n"
                f"Ce lien est valable 7 jours.\n\n"
                f"Cordialement,\nL'équipe SCORE"
            ),
            from_email     = settings.EMAIL_HOST_USER,
            recipient_list = [debt.customer.email],
            fail_silently  = False,
        )

        return Response(
            {"message": "Lien de validation envoyé au client par email."},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Customers - Dettes"],
    summary="Valider une dette via lien unique",
    description="Le client valide la dette via le lien reçu par email. Aucune authentification requise.",
    request=None,
    responses=None,
)
class DebtValidateView(APIView):
    permission_classes = []

    def get(self, request):
        token = request.query_params.get('token')

        if not token:
            return Response(
                {"error": "Token manquant."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            debt = Debt.objects.get(validation_token=token)
        except Debt.DoesNotExist:
            return Response(
                {"error": "Lien invalide."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not debt.is_validation_token_valid():
            return Response(
                {"error": "Ce lien a expiré ou a déjà été utilisé."},
                status=status.HTTP_400_BAD_REQUEST
            )

        debt.validation_status       = 'validated'
        debt.validation_token        = None
        debt.validation_token_expiry = None
        debt.save(update_fields=[
            'validation_status',
            'validation_token',
            'validation_token_expiry',
        ])

        return Response(
            {"message": "Dette validée avec succès. Merci."},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Customers - Dettes"],
    summary="Refuser une dette via lien unique",
    description="Le client refuse la dette via le lien reçu par email. Aucune authentification requise.",
    request=None,
    responses=None,
)
class DebtRejectView(APIView):
    permission_classes = []

    def get(self, request):
        token = request.query_params.get('token')

        if not token:
            return Response(
                {"error": "Token manquant."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            debt = Debt.objects.get(validation_token=token)
        except Debt.DoesNotExist:
            return Response(
                {"error": "Lien invalide."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not debt.is_validation_token_valid():
            return Response(
                {"error": "Ce lien a expiré ou a déjà été utilisé."},
                status=status.HTTP_400_BAD_REQUEST
            )

        debt.validation_status       = 'rejected'
        debt.validation_token        = None
        debt.validation_token_expiry = None
        debt.save(update_fields=[
            'validation_status',
            'validation_token',
            'validation_token_expiry',
        ])

        return Response(
            {"message": "Dette refusée. L'huissier sera notifié pour correction."},
            status=status.HTTP_200_OK
        )


# ─────────────────────────────────────────────
# VALIDATION REMBOURSEMENT PAR LIEN UNIQUE
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Customers - Remboursements"],
    summary="Envoyer le lien de validation d'un remboursement",
    description="Envoie un lien unique au client pour valider ou refuser le remboursement.",
    request=None,
    responses=None,
)
class RepaymentSendValidationView(APIView):
    permission_classes = [IsHuissier]

    def post(self, request, pk):
        try:
            repayment = Repayment.objects.get(pk=pk)
        except Repayment.DoesNotExist:
            return Response(
                {"error": "Remboursement introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not repayment.is_editable():
            return Response(
                {"error": "Ce remboursement a déjà été validé par le client."},
                status=status.HTTP_400_BAD_REQUEST
            )

        token = repayment.generate_validation_token()

        base_url     = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        validate_url = f"{base_url}/repayments/validate/?token={token}"
        reject_url   = f"{base_url}/repayments/reject/?token={token}"

        customer = repayment.debt.customer
        send_mail(
            subject        = "[SCORE] Confirmation de remboursement",
            message        = (
                f"Bonjour {customer.full_name},\n\n"
                f"Un remboursement a été enregistré pour votre dette :\n"
                f"- Date          : {repayment.date}\n"
                f"- Montant dette : {repayment.debt.amount}\n\n"
                f"Pour VALIDER ce remboursement, cliquez ici :\n{validate_url}\n\n"
                f"Pour REFUSER ce remboursement, cliquez ici :\n{reject_url}\n\n"
                f"Ce lien est valable 7 jours.\n\n"
                f"Cordialement,\nL'équipe SCORE"
            ),
            from_email     = settings.EMAIL_HOST_USER,
            recipient_list = [customer.email],
            fail_silently  = False,
        )

        return Response(
            {"message": "Lien de validation envoyé au client par email."},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Customers - Remboursements"],
    summary="Valider un remboursement via lien unique",
    description="Le client valide le remboursement via le lien reçu par email. Aucune authentification requise.",
    request=None,
    responses=None,
)
class RepaymentValidateView(APIView):
    permission_classes = []

    def get(self, request):
        token = request.query_params.get('token')

        if not token:
            return Response(
                {"error": "Token manquant."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            repayment = Repayment.objects.get(validation_token=token)
        except Repayment.DoesNotExist:
            return Response(
                {"error": "Lien invalide."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not repayment.is_validation_token_valid():
            return Response(
                {"error": "Ce lien a expiré ou a déjà été utilisé."},
                status=status.HTTP_400_BAD_REQUEST
            )

        repayment.validation_status       = 'validated'
        repayment.validation_token        = None
        repayment.validation_token_expiry = None
        repayment.save(update_fields=[
            'validation_status',
            'validation_token',
            'validation_token_expiry',
        ])

        return Response(
            {"message": "Remboursement validé avec succès. Merci."},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Customers - Remboursements"],
    summary="Refuser un remboursement via lien unique",
    description="Le client refuse le remboursement via le lien reçu par email. Aucune authentification requise.",
    request=None,
    responses=None,
)
class RepaymentRejectView(APIView):
    permission_classes = []

    def get(self, request):
        token = request.query_params.get('token')

        if not token:
            return Response(
                {"error": "Token manquant."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            repayment = Repayment.objects.get(validation_token=token)
        except Repayment.DoesNotExist:
            return Response(
                {"error": "Lien invalide."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not repayment.is_validation_token_valid():
            return Response(
                {"error": "Ce lien a expiré ou a déjà été utilisé."},
                status=status.HTTP_400_BAD_REQUEST
            )

        repayment.validation_status       = 'rejected'
        repayment.validation_token        = None
        repayment.validation_token_expiry = None
        repayment.save(update_fields=[
            'validation_status',
            'validation_token',
            'validation_token_expiry',
        ])

        return Response(
            {"message": "Remboursement refusé. L'huissier sera notifié pour correction."},
            status=status.HTTP_200_OK
        )