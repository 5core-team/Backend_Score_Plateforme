from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.utils import timezone
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework import status, generics
from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from .models import ScoreUser, AccountCredentials, PasswordResetCodeModel
from .serializers import (
    LoginSerializer,
    LoginResponseSerializer,
    UserProfileSerializer,
    ErrorSerializer,
)
from accounts.utils import send_email

import random
import uuid
from datetime import timedelta


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class Login(APIView):

    @extend_schema(
        tags=["Auth"],
        summary="Connexion utilisateur",
        description="Authentification par email/password. Retourne les tokens JWT.",
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: OpenApiResponse(description="Identifiants invalides"),
            403: OpenApiResponse(description="Compte inactif"),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email    = serializer.validated_data.get("email")
        password = serializer.validated_data.get("password")

        user = authenticate(request, username=email, password=password)

        if not user:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            return Response({"error": "Account is inactive"}, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        return Response({
            "access_token":  str(refresh.access_token),
            "refresh_token": str(refresh),
            "type_user":     user.role
        }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# VERIFY PASSWORD SETUP CREDENTIALS
# ─────────────────────────────────────────────

class VerifyPasswordSetupCredentials(APIView):

    @extend_schema(
        tags=["Auth"],
        summary="Vérifier les credentials pour setup du mot de passe",
        description="Vérifie si le uid et le token sont valides avant de permettre à l'utilisateur de définir son mot de passe.",
        parameters=[
            OpenApiParameter(name="uid",   type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name="token", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=True),
        ],
        responses={
            200: OpenApiResponse(description="Token valide"),
            400: OpenApiResponse(response=ErrorSerializer, description="Paramètres invalides ou token expiré"),
        },
    )
    def get(self, request):
        uid   = request.query_params.get("uid")
        token = request.query_params.get("token")

        if not uid or not token:
            return Response({"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user    = get_object_or_404(ScoreUser, pk=user_id)
        except Exception:
            return Response({"error": "Invalid uid"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            account_cred = AccountCredentials.objects.get(user=user, token=token)
        except AccountCredentials.DoesNotExist:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Utilisation de la property is_expired du modèle
        if account_cred.is_expired:
            return Response({"error": "Token expired"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"msg": "Token is valid"}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# PASSWORD SETUP
# ─────────────────────────────────────────────

class PasswordSetup(APIView):

    @extend_schema(
        tags=["Auth"],
        summary="Définir le mot de passe initial",
        description="Permet à un utilisateur de définir son mot de passe via uid et token reçus par email.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "uid":      {"type": "string"},
                    "token":    {"type": "string"},
                    "password": {"type": "string"},
                },
                "required": ["uid", "token", "password"],
            }
        },
        responses={
            200: OpenApiResponse(description="Mot de passe défini avec succès"),
            400: OpenApiResponse(response=ErrorSerializer, description="Paramètres invalides ou token expiré"),
        },
    )
    def post(self, request):
        uid      = request.data.get("uid")
        token    = request.data.get("token")
        password = request.data.get("password")

        if not uid or not token or not password:
            return Response({"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user    = get_object_or_404(ScoreUser, pk=user_id)
        except Exception:
            return Response({"error": "Invalid uid"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            credentials = AccountCredentials.objects.get(user=user, token=token)
        except AccountCredentials.DoesNotExist:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Utilisation de la property is_expired du modèle
        if credentials.is_expired:
            return Response({"error": "Token expired"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.is_active        = True
        user.password_changed = True
        user.save()
        credentials.delete()

        return Response({"msg": "Password set successfully"}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# PASSWORD RESET CODE
# ─────────────────────────────────────────────

class PasswordResetCode(APIView):

    @extend_schema(
        tags=["Auth"],
        summary="Demander un code de réinitialisation",
        description="Envoie un code OTP à 6 chiffres par email. Limité à 4 tentatives/jour avec 90s entre chaque.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "format": "email"},
                },
                "required": ["email"],
            }
        },
        responses={
            200: OpenApiResponse(description="Code généré avec succès"),
            400: OpenApiResponse(description="Email manquant"),
            429: OpenApiResponse(description="Trop de tentatives ou délai non respecté"),
        },
    )
    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        user        = get_object_or_404(ScoreUser, email=email)
        today       = timezone.now().date()
        codes_today = PasswordResetCodeModel.objects.filter(user=user, created_at__date=today)

        if codes_today.count() >= 4:
            return Response(
                {"error": "Maximum number of reset attempts reached today"},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        last_code = codes_today.order_by('-created_at').first()
        if last_code and timezone.now() - last_code.created_at < timedelta(seconds=90):
            return Response(
                {"error": "Wait before requesting a new code"},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        code = str(random.randint(100000, 999999))
        PasswordResetCodeModel.objects.create(
            user=user,
            code=code,
            expiry_date=timezone.now() + timedelta(minutes=10)
        )

        send_email({
            "subject": "Code de réinitialisation Score",
            "message": (
                f"Bonjour {user.username},\n\n"
                f"Votre code de réinitialisation est : {code}\n\n"
                f"Ce code est valable 10 minutes.\n\n"
                f"Si vous n'avez pas demandé ce code, ignorez cet email.\n\n"
                f"Cordialement,\nL'équipe SCORE"
            ),
            "to": user.email
        })

        return Response({"msg": "Reset code generated successfully"}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# VERIFY VALIDATION CODE
# ─────────────────────────────────────────────

class VerifyValidationCode(APIView):

    @extend_schema(
        tags=["Auth"],
        summary="Vérifier le code OTP reçu par email",
        description="Valide le code OTP et retourne un token de réinitialisation.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "code":  {"type": "string"},
                },
                "required": ["email", "code"],
            }
        },
        responses={
            200: OpenApiResponse(description="Token de reset retourné"),
            400: OpenApiResponse(description="Code invalide ou expiré"),
        },
    )
    def post(self, request):
        email = request.data.get("email")
        code  = request.data.get("code")

        if not email or not code:
            return Response({"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST)

        user       = get_object_or_404(ScoreUser, email=email)
        reset_code = PasswordResetCodeModel.objects.filter(
            user=user, code=code
        ).order_by('-created_at').first()

        if not reset_code:
            return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Vérifier l'expiration AVANT de créer le token — et nettoyer le code expiré
        if reset_code.expiry_date < timezone.now():
            reset_code.delete()
            return Response({"error": "Code expired"}, status=status.HTTP_400_BAD_REQUEST)

        token          = str(uuid.uuid4())
        expiry_minutes = getattr(settings, "RESET_TOKEN_EXPIRY_MINUTES", 15)

        AccountCredentials.objects.create(
            user=user,
            token=token,
            expiry_date=timezone.now() + timedelta(minutes=expiry_minutes)
        )

        reset_code.delete()

        return Response(
            {
                "reset_token": token,
                "expires_in":  expiry_minutes * 60
            },
            status=status.HTTP_200_OK
        )


# ─────────────────────────────────────────────
# RESET PASSWORD
# ─────────────────────────────────────────────

class ResetPassword(APIView):

    @extend_schema(
        tags=["Auth"],
        summary="Réinitialiser le mot de passe",
        description="Réinitialise le mot de passe avec le token reçu après validation du code OTP.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "token":    {"type": "string"},
                    "password": {"type": "string"},
                },
                "required": ["token", "password"],
            }
        },
        responses={
            200: OpenApiResponse(description="Mot de passe réinitialisé avec succès"),
            400: OpenApiResponse(description="Token invalide ou expiré"),
        },
    )
    def post(self, request):
        token    = request.data.get("token")
        password = request.data.get("password")

        if not token or not password:
            return Response({"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST)

        credentials = AccountCredentials.objects.filter(token=token).first()

        if not credentials:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Utilisation de la property is_expired + nettoyage du token expiré
        if credentials.is_expired:
            credentials.delete()
            return Response({"error": "Token expired"}, status=status.HTTP_400_BAD_REQUEST)

        user = credentials.user
        user.set_password(password)
        user.save()
        credentials.delete()

        return Response({"msg": "Password reset successfully"}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# CHANGE PASSWORD
# ─────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class ChangePassword(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Changer le mot de passe",
        description="Permet à un utilisateur authentifié de changer son mot de passe. Retourne de nouveaux tokens JWT.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "old_password": {"type": "string"},
                    "new_password": {"type": "string"},
                },
                "required": ["old_password", "new_password"],
            }
        },
        responses={
            200: OpenApiResponse(description="Mot de passe modifié avec succès — nouveaux tokens retournés"),
            400: OpenApiResponse(description="Ancien mot de passe incorrect ou paramètres manquants"),
        },
    )
    def post(self, request: Request):
        user         = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            return Response(
                {"error": "Ancien et nouveau mot de passe requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(old_password):
            return Response(
                {"error": "Ancien mot de passe incorrect."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.password_changed = True
        user.save()

        # ✅ Nouveaux tokens JWT retournés — l'ancien token est invalidé
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message":       "Mot de passe modifié avec succès.",
                "access_token":  str(refresh.access_token),
                "refresh_token": str(refresh),
            },
            status=status.HTTP_200_OK
        )


# ─────────────────────────────────────────────
# PROFILE VIEW
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Profil"],
    summary="Récupérer et mettre à jour le profil utilisateur",
    description="GET → récupérer le profil | PUT/PATCH → modifier le profil.",
    request=UserProfileSerializer,
    responses={
        200: UserProfileSerializer,
        400: OpenApiResponse(description="Données invalides"),
    },
)
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class   = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user