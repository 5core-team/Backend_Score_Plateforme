from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, BasePermission, SAFE_METHODS
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

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
    """
    Vérifie qu'une session de consultation est valide
    pour un client donné.
    """
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
            return Customer.objects.all()  # ✅ accès à tous les clients
        return Customer.objects.none()

    # ─────────────────────────────────────────
    # RECHERCHE CLIENT
    # ─────────────────────────────────────────

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

    # ─────────────────────────────────────────
    # DEMANDE D'OTP
    # ─────────────────────────────────────────

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

    # ─────────────────────────────────────────
    # VÉRIFICATION OTP + OUVERTURE SESSION
    # ─────────────────────────────────────────

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

        # Marquer l'OTP comme utilisé
        otp.is_used = True
        otp.save()

        # Créer une session de consultation
        expiry_mins = getattr(settings, "CONSULTATION_SESSION_EXPIRY_MINUTES", 30)
        session = ConsultationSession.objects.create(
            customer=customer,
            created_by=request.user,
            expiry_date=timezone.now() + timedelta(minutes=expiry_mins),
        )

        return Response(
            {
                "msg": "Session de consultation ouverte.",
                "session_token": str(session.token),
                "customer":      CustomerSerializer(customer).data,
                "expires_in":    expiry_mins * 60,  # en secondes
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
        description="Réservé à l'huissier uniquement. Nécessite un session_token valide.",
        request=DebtSerializer,
        responses={200: DebtSerializer},
    ),
    partial_update=extend_schema(
        tags=["Customers - Dettes"],
        summary="Modifier partiellement une dette",
        request=DebtSerializer,
        responses={200: DebtSerializer},
    ),
    destroy=extend_schema(
        tags=["Customers - Dettes"],
        summary="Supprimer une dette",
        responses={204: OpenApiResponse(description="Dette supprimée")},
    ),
)
class DebtViewSet(viewsets.ModelViewSet):
    serializer_class   = DebtSerializer
    lookup_value_regex = r'\d+'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHuissier()]
        return [IsHuissierOrAdvisor()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Debt.objects.all()
        if user.role in ['huissier', 'conseiller']:
            return Debt.objects.all()  # ✅ accès à toutes les dettes
        return Debt.objects.none()

    def create(self, request, *args, **kwargs):
        # ✅ Vérifier la session de consultation
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
        request=RepaymentSerializer,
        responses={200: RepaymentSerializer},
    ),
    partial_update=extend_schema(
        tags=["Customers - Remboursements"],
        summary="Modifier partiellement un remboursement",
        request=RepaymentSerializer,
        responses={200: RepaymentSerializer},
    ),
    destroy=extend_schema(
        tags=["Customers - Remboursements"],
        summary="Supprimer un remboursement",
        responses={204: OpenApiResponse(description="Remboursement supprimé")},
    ),
)
class RepaymentViewSet(viewsets.ModelViewSet):
    serializer_class   = RepaymentSerializer
    lookup_value_regex = r'\d+'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHuissier()]
        return [IsHuissierOrAdvisor()]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Repayment.objects.all()
        if user.role in ['huissier', 'conseiller']:
            return Repayment.objects.all()  # ✅ accès à tous les remboursements
        return Repayment.objects.none()

    def create(self, request, *args, **kwargs):
        # ✅ Vérifier la session de consultation
        session_token = request.data.get('session_token')
        debt_id       = request.data.get('debt')

        if not session_token:
            return Response(
                {"error": "session_token requis pour ajouter un remboursement."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupérer le customer via la dette
        try:
            from .models import Debt as DebtModel
            debt        = DebtModel.objects.get(id=debt_id)
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