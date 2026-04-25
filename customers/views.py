from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, BasePermission, SAFE_METHODS
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiResponse, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

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
from accounts.utils import send_email


# ─────────────────────────────────────────────
# PERMISSIONS
# ─────────────────────────────────────────────

class IsHuissier(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'huissier'


class IsHuissierOrAdvisor(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        return user.role in ['huissier', 'conseiller']


# ─────────────────────────────────────────────
# HELPER — Vérification session de consultation
# ─────────────────────────────────────────────

def get_valid_session(session_token, customer_uuid):
    try:
        session = ConsultationSession.objects.get(
            token=session_token,
            customer__uuid=customer_uuid,
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
        description="Réservé à l'huissier uniquement. Zone, sous-zone et huissier sont déduits automatiquement depuis le profil de l'huissier connecté.",
        request=CustomerSerializer,
        responses={
            201: CustomerSerializer,
            400: OpenApiResponse(description="Données invalides"),
            403: OpenApiResponse(description="Permission refusée"),
        },
    ),
)
class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class   = CustomerSerializer
    lookup_field       = 'uuid'
    lookup_value_regex = r'[0-9a-f-]+'

    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        if self.action == 'create':
            return [IsHuissier()]
        return [IsHuissierOrAdvisor()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Customer.objects.all()
        if user.role in ['huissier', 'conseiller']:
            return Customer.objects.all()
        return Customer.objects.none()

    def create(self, request, *args, **kwargs):
        from staff.models import Huissier

        try:
            huissier = Huissier.objects.get(user=request.user)
        except Huissier.DoesNotExist:
            return Response(
                {"error": "Aucun profil huissier associé à votre compte."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            zone     = huissier.zone,
            subZone  = huissier.subZone,
            huissier = huissier,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Customers"],
        summary="Rechercher un client",
        description="Recherche par NPI uniquement.",
        parameters=[
            OpenApiParameter(
                name='npi',
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Numéro Personnel d'Identification (NPI)"
            ),
        ],
        responses={200: CustomerSearchSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], url_path='search', permission_classes=[IsHuissierOrAdvisor])
    def search(self, request):
        npi = request.query_params.get('npi', '').strip()
        if not npi:
            return Response(
                {"error": "Paramètre 'npi' requis."},
                status=status.HTTP_400_BAD_REQUEST
            )
        customers  = Customer.objects.filter(npi=npi)
        serializer = CustomerSearchSerializer(customers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Customers"],
        summary="Demander un code OTP de consultation",
        description="Accessible à l'huissier ET au conseiller financier. Envoie un code OTP par mail au client pour autoriser la consultation.",
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
        description="Accessible à l'huissier ET au conseiller financier. Valide le code OTP et retourne un token de session valable 30 minutes.",
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
        summary="Lister les dettes d'un client",
        description="Retourne les dettes d'un client spécifique via son customer_uuid en paramètre.",
        parameters=[
            OpenApiParameter(
                name='customer_uuid',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=True,
                description="UUID du client dont on veut lister les dettes"
            ),
        ],
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
        description=(
            "Réservé à l'huissier uniquement. Nécessite un session_token valide.\n\n"
            "**Champs à envoyer :**\n"
            "- `session_token` : token retourné par verify-otp\n"
            "- `customer_uuid_field` : UUID du client retourné par verify-otp\n"
            "- `creditor` : ID du créditeur (optionnel)\n"
            "- `amount` : montant total (ex: 150000.00)\n"
            "- `deadline_amount` : montant par échéance (ex: 12500.00)\n"
            "- `periodicity` : daily | weekly | monthly | quarterly | biannual | annual\n"
            "- `deadline` : date limite YYYY-MM-DD\n"
            "- `status` : toujours 'pending' à la création"
        ),
        request=DebtSerializer,
        examples=[
            OpenApiExample(
                name="Créer une dette",
                value={
                    "session_token":       "550e8400-e29b-41d4-a716-446655440000",
                    "customer_uuid_field": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "creditor":            None,
                    "amount":              "150000.00",
                    "deadline_amount":     "12500.00",
                    "periodicity":         "monthly",
                    "deadline":            "2027-04-25",
                    "status":              "pending",
                },
                request_only=True,
            )
        ],
        responses={
            201: OpenApiResponse(
                description="Dette créée avec succès",
                response=DebtSerializer,
                examples=[
                    OpenApiExample(
                        name="Exemple de dette créée",
                        value={
                            "uuid":             "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                            "id":               1,
                            "customer":         1,
                            "customer_uuid":    "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                            "customer_name":    "Dora Barbouche",
                            "creditor_name":    None,
                            "amount":           "150000.00",
                            "deadline_amount":  "12500.00",
                            "periodicity":      "monthly",
                            "deadline":         "2027-04-25",
                            "verified":         False,
                            "status":           "pending",
                            "validation_status":"pending",
                            "is_monitored":     False,
                            "created_at":       "2026-04-25",
                            "updated_at":       "2026-04-25",
                            "repayments":       []
                        },
                        response_only=True,
                    )
                ]
            ),
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
    lookup_field       = 'uuid'
    lookup_value_regex = r'[0-9a-f-]+'

    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'toggle_monitoring', 'send_validation']:
            return [IsHuissier()]
        return [IsHuissierOrAdvisor()]

    def get_queryset(self):
        user          = self.request.user
        customer_uuid = self.request.query_params.get('customer_uuid')

        if not user.is_authenticated:
            return Debt.objects.none()
        if not customer_uuid:
            return Debt.objects.none()
        if user.is_superuser:
            return Debt.objects.filter(customer__uuid=customer_uuid)
        if user.role in ['huissier', 'conseiller']:
            return Debt.objects.filter(customer__uuid=customer_uuid)
        return Debt.objects.none()

    def list(self, request, *args, **kwargs):
        if not request.query_params.get('customer_uuid'):
            return Response(
                {"error": "Le paramètre 'customer_uuid' est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        session_token = request.data.get('session_token')
        # ✅ customer_uuid_field — nom exact du champ dans le serializer
        customer_uuid = request.data.get('customer_uuid_field')

        if not session_token:
            return Response(
                {"error": "session_token requis pour ajouter une dette."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not customer_uuid:
            return Response(
                {"error": "customer_uuid_field requis pour ajouter une dette."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Vérifier que la session est valide et appartient bien au client
        session, error = get_valid_session(session_token, customer_uuid)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # ✅ customer déduit depuis la session
        serializer.save(customer=session.customer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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

    @extend_schema(
        tags=["Customers - Dettes"],
        summary="Activer/désactiver le suivi d'une dette",
        description="L'huissier active ou désactive le suivi d'une dette. Uniquement pour les dettes validées.",
        request=None,
        responses=None,
    )
    @action(detail=True, methods=['post'], url_path='toggle-monitoring', permission_classes=[IsHuissier])
    def toggle_monitoring(self, request, uuid=None):
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

    @extend_schema(
        tags=["Customers - Dettes"],
        summary="Envoyer le lien de validation d'une dette",
        description="Envoie un lien unique au client pour valider ou refuser la dette.",
        request=None,
        responses=None,
    )
    @action(detail=True, methods=['post'], url_path='send-validation', permission_classes=[IsHuissier])
    def send_validation(self, request, uuid=None):
        debt = self.get_object()

        if not debt.is_editable():
            return Response(
                {"error": "Cette dette a déjà été validée par le client."},
                status=status.HTTP_400_BAD_REQUEST
            )

        token        = debt.generate_validation_token()
        base_url     = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        validate_url = f"{base_url}/debts/validate/?token={token}"
        reject_url   = f"{base_url}/debts/reject/?token={token}"

        send_email({
            "subject": "[SCORE] Confirmation d'enregistrement de dette",
            "message": (
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
            "to": debt.customer.email,
        })

        return Response(
            {"message": "Lien de validation envoyé au client par email."},
            status=status.HTTP_200_OK
        )


# ─────────────────────────────────────────────
# REPAYMENT VIEWSET
# ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=["Customers - Remboursements"],
        summary="Lister les remboursements d'un client",
        description="Retourne les remboursements d'un client spécifique via son customer_uuid en paramètre.",
        parameters=[
            OpenApiParameter(
                name='customer_uuid',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                required=True,
                description="UUID du client dont on veut lister les remboursements"
            ),
        ],
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
        description=(
            "Réservé à l'huissier uniquement. Nécessite un session_token valide.\n\n"
            "**Champs à envoyer :**\n"
            "- `session_token` : token retourné par verify-otp\n"
            "- `debt_uuid` : UUID de la dette concernée\n"
            "- `amount` : montant du versement (ex: 5000.00)\n"
            "- `date` : date du remboursement (YYYY-MM-DD)"
        ),
        request=RepaymentSerializer,
        examples=[
            OpenApiExample(
                name="Créer un remboursement",
                value={
                    "session_token": "550e8400-e29b-41d4-a716-446655440000",
                    "debt_uuid":     "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "amount":        "5000.00",
                    "date":          "2026-04-25",
                },
                request_only=True,
            )
        ],
        responses={
            201: OpenApiResponse(
                description="Remboursement créé avec succès",
                response=RepaymentSerializer,
                examples=[
                    OpenApiExample(
                        name="Exemple de remboursement créé",
                        value={
                            "uuid":              "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                            "debt":              1,
                            "amount":            "5000.00",
                            "date":              "2026-04-25",
                            "validation_status": "pending",
                        },
                        response_only=True,
                    )
                ]
            ),
            400: OpenApiResponse(description="Session invalide ou dette introuvable"),
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
    lookup_field       = 'uuid'
    lookup_value_regex = r'[0-9a-f-]+'

    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'send_validation']:
            return [IsHuissier()]
        return [IsHuissierOrAdvisor()]

    def get_queryset(self):
        user          = self.request.user
        customer_uuid = self.request.query_params.get('customer_uuid')

        if not user.is_authenticated:
            return Repayment.objects.none()
        if not customer_uuid:
            return Repayment.objects.none()
        if user.is_superuser:
            return Repayment.objects.filter(debt__customer__uuid=customer_uuid)
        if user.role in ['huissier', 'conseiller']:
            return Repayment.objects.filter(debt__customer__uuid=customer_uuid)
        return Repayment.objects.none()

    def list(self, request, *args, **kwargs):
        if not request.query_params.get('customer_uuid'):
            return Response(
                {"error": "Le paramètre 'customer_uuid' est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        session_token = request.data.get('session_token')
        debt_uuid     = request.data.get('debt_uuid')

        if not session_token:
            return Response(
                {"error": "session_token requis pour ajouter un remboursement."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not debt_uuid:
            return Response(
                {"error": "debt_uuid requis pour ajouter un remboursement."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Récupérer la dette depuis son UUID
        try:
            debt          = Debt.objects.get(uuid=debt_uuid)
            customer_uuid = str(debt.customer.uuid)
        except Debt.DoesNotExist:
            return Response(
                {"error": "Dette introuvable."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Vérifier que la session appartient bien au client de cette dette
        session, error = get_valid_session(session_token, customer_uuid)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # ✅ debt injecté via save()
        serializer.save(debt=debt)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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

    @extend_schema(
        tags=["Customers - Remboursements"],
        summary="Envoyer le lien de validation d'un remboursement",
        description=(
            "Envoie un lien unique au client pour valider ou refuser le remboursement. "
            "L'email contient le montant du versement et le montant total de la dette."
        ),
        request=None,
        responses=None,
    )
    @action(detail=True, methods=['post'], url_path='send-validation', permission_classes=[IsHuissier])
    def send_validation(self, request, uuid=None):
        repayment = self.get_object()

        if not repayment.is_editable():
            return Response(
                {"error": "Ce remboursement a déjà été validé par le client."},
                status=status.HTTP_400_BAD_REQUEST
            )

        token        = repayment.generate_validation_token()
        base_url     = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        validate_url = f"{base_url}/repayments/validate/?token={token}"
        reject_url   = f"{base_url}/repayments/reject/?token={token}"

        customer = repayment.debt.customer
        send_email({
            "subject": "[SCORE] Confirmation de remboursement",
            "message": (
                f"Bonjour {customer.full_name},\n\n"
                f"Un remboursement a été enregistré pour votre dette :\n"
                f"- Montant versé  : {repayment.amount}\n"
                f"- Date           : {repayment.date}\n"
                f"- Montant dette  : {repayment.debt.amount}\n\n"
                f"Pour VALIDER ce remboursement, cliquez ici :\n{validate_url}\n\n"
                f"Pour REFUSER ce remboursement, cliquez ici :\n{reject_url}\n\n"
                f"Ce lien est valable 7 jours.\n\n"
                f"Cordialement,\nL'équipe SCORE"
            ),
            "to": customer.email,
        })

        return Response(
            {"message": "Lien de validation envoyé au client par email."},
            status=status.HTTP_200_OK
        )


# ─────────────────────────────────────────────
# VALIDATION DETTE PAR LIEN UNIQUE
# ─────────────────────────────────────────────

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
            return Response({"error": "Token manquant."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            debt = Debt.objects.get(validation_token=token)
        except Debt.DoesNotExist:
            return Response({"error": "Lien invalide."}, status=status.HTTP_400_BAD_REQUEST)
        if not debt.is_validation_token_valid():
            return Response({"error": "Ce lien a expiré ou a déjà été utilisé."}, status=status.HTTP_400_BAD_REQUEST)
        debt.validation_status       = 'validated'
        debt.validation_token        = None
        debt.validation_token_expiry = None
        debt.save(update_fields=['validation_status', 'validation_token', 'validation_token_expiry'])
        return Response({"message": "Dette validée avec succès. Merci."}, status=status.HTTP_200_OK)


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
            return Response({"error": "Token manquant."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            debt = Debt.objects.get(validation_token=token)
        except Debt.DoesNotExist:
            return Response({"error": "Lien invalide."}, status=status.HTTP_400_BAD_REQUEST)
        if not debt.is_validation_token_valid():
            return Response({"error": "Ce lien a expiré ou a déjà été utilisé."}, status=status.HTTP_400_BAD_REQUEST)
        debt.validation_status       = 'rejected'
        debt.validation_token        = None
        debt.validation_token_expiry = None
        debt.save(update_fields=['validation_status', 'validation_token', 'validation_token_expiry'])
        return Response({"message": "Dette refusée. L'huissier sera notifié pour correction."}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# VALIDATION REMBOURSEMENT PAR LIEN UNIQUE
# ─────────────────────────────────────────────

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
            return Response({"error": "Token manquant."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            repayment = Repayment.objects.get(validation_token=token)
        except Repayment.DoesNotExist:
            return Response({"error": "Lien invalide."}, status=status.HTTP_400_BAD_REQUEST)
        if not repayment.is_validation_token_valid():
            return Response({"error": "Ce lien a expiré ou a déjà été utilisé."}, status=status.HTTP_400_BAD_REQUEST)

        repayment.validation_status       = 'validated'
        repayment.validation_token        = None
        repayment.validation_token_expiry = None
        repayment.save(update_fields=['validation_status', 'validation_token', 'validation_token_expiry'])

        # ✅ Vérifier si la dette est entièrement remboursée
        # Somme de tous les remboursements validés >= montant total de la dette → status = 'done'
        from django.db.models import Sum
        debt            = repayment.debt
        total_rembourse = Repayment.objects.filter(
            debt=debt,
            validation_status='validated'
        ).aggregate(total=Sum('amount'))['total'] or 0

        if total_rembourse >= debt.amount:
            debt.status = 'done'
            debt.save(update_fields=['status'])

        return Response({"message": "Remboursement validé avec succès. Merci."}, status=status.HTTP_200_OK)


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
            return Response({"error": "Token manquant."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            repayment = Repayment.objects.get(validation_token=token)
        except Repayment.DoesNotExist:
            return Response({"error": "Lien invalide."}, status=status.HTTP_400_BAD_REQUEST)
        if not repayment.is_validation_token_valid():
            return Response({"error": "Ce lien a expiré ou a déjà été utilisé."}, status=status.HTTP_400_BAD_REQUEST)
        repayment.validation_status       = 'rejected'
        repayment.validation_token        = None
        repayment.validation_token_expiry = None
        repayment.save(update_fields=['validation_status', 'validation_token', 'validation_token_expiry'])
        return Response({"message": "Remboursement refusé. L'huissier sera notifié pour correction."}, status=status.HTTP_200_OK)