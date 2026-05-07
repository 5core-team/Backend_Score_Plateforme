from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.hashers import make_password

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework import status, generics, parsers
from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from .models import ScoreUser, AccountCredentials, PasswordResetCodeModel, PasswordChangeRequest
from .serializers import (
    LoginSerializer,
    LoginResponseSerializer,
    UserProfileSerializer,
    UpdateUsernameSerializer,
    UpdatePhotoSerializer,
    ChangePasswordRequestSerializer,
    ErrorSerializer,
)
from accounts.utils import send_email

import secrets
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

        if credentials.is_expired:
            credentials.delete()
            return Response({"error": "Token expired"}, status=status.HTTP_400_BAD_REQUEST)

        user = credentials.user
        user.set_password(password)
        user.save()
        credentials.delete()

        return Response({"msg": "Password reset successfully"}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# PROFILE VIEW — GET uniquement
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Profil"],
    summary="Récupérer le profil utilisateur",
    description="Retourne les informations du profil de l'utilisateur connecté.",
    responses={200: UserProfileSerializer},
)
class ProfileView(generics.RetrieveAPIView):
    serializer_class   = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# ─────────────────────────────────────────────
# UPDATE USERNAME — PATCH username uniquement
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Profil"],
    summary="Modifier le nom d'utilisateur",
    description="Permet de modifier uniquement le nom d'utilisateur.",
    request=UpdateUsernameSerializer,
    responses={
        200: UpdateUsernameSerializer,
        400: OpenApiResponse(description="Nom d'utilisateur invalide ou déjà utilisé"),
    },
)
class UpdateUsernameView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = UpdateUsernameSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "message": "Nom d'utilisateur mis à jour avec succès.",
                "data":    serializer.data,
            },
            status=status.HTTP_200_OK
        )


# ─────────────────────────────────────────────
# UPDATE PHOTO — PATCH photo uniquement
# multipart/form-data requis
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Profil"],
    summary="Modifier la photo de profil",
    description="Permet de modifier uniquement la photo de profil. Envoyer en multipart/form-data.",
    request=UpdatePhotoSerializer,
    responses={
        200: UpdatePhotoSerializer,
        400: OpenApiResponse(description="Fichier invalide"),
    },
)
class UpdatePhotoView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [parsers.MultiPartParser, parsers.FormParser]

    def patch(self, request):
        serializer = UpdatePhotoSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "message": "Photo de profil mise à jour avec succès.",
                "data":    serializer.data,
            },
            status=status.HTTP_200_OK
        )


# ─────────────────────────────────────────────
# CHANGE PASSWORD REQUEST — via email
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Profil"],
    summary="Demander un changement de mot de passe",
    description=(
        "L'utilisateur saisit son nouveau mot de passe et sa confirmation. "
        "Un email de confirmation est envoyé automatiquement. "
        "L'ancien mot de passe reste actif jusqu'à confirmation du lien reçu par email."
    ),
    request=ChangePasswordRequestSerializer,
    responses={
        200: OpenApiResponse(description="Email de confirmation envoyé"),
        400: OpenApiResponse(description="Mots de passe invalides ou non identiques"),
    },
)
class ChangePasswordRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user         = request.user
        new_password = serializer.validated_data['new_password']

        # ✅ Hasher le nouveau mot de passe avant de le stocker
        new_password_hash = make_password(new_password)

        # ✅ Supprimer les anciennes demandes non confirmées
        PasswordChangeRequest.objects.filter(user=user, is_used=False).delete()

        # ✅ Créer la demande avec un token unique
        token = secrets.token_urlsafe(32)
        PasswordChangeRequest.objects.create(
            user              = user,
            new_password_hash = new_password_hash,
            token             = token,
            expiry_date       = timezone.now() + timedelta(minutes=30),
        )

        # ✅ Envoyer l'email de confirmation
        base_url    = getattr(settings, 'FRONTEND_URL', "https://africarisque.com")
        confirm_url = f"{base_url}/profile/confirm-password/?token={token}"

        send_email({
            "subject": "[SCORE] Confirmation de changement de mot de passe",
            "message": (
                f"Bonjour {user.username},\n\n"
                f"Vous avez demandé à changer votre mot de passe.\n\n"
                f"Cliquez sur le lien ci-dessous pour confirmer :\n{confirm_url}\n\n"
                f"Ce lien est valable 30 minutes.\n\n"
                f"Si vous n'avez pas fait cette demande, ignorez cet email.\n"
                f"Votre ancien mot de passe reste actif.\n\n"
                f"Cordialement,\nL'équipe SCORE"
            ),
            "to": user.email,
        })

        return Response(
            {"message": "Email de confirmation envoyé. Vérifiez votre boîte mail."},
            status=status.HTTP_200_OK
        )


# ─────────────────────────────────────────────
# CONFIRM PASSWORD CHANGE — via lien email
# ─────────────────────────────────────────────

@extend_schema(
    tags=["Profil"],
    summary="Confirmer le changement de mot de passe",
    description="Le lien reçu par email active le nouveau mot de passe. Aucune authentification requise.",
    parameters=[
        OpenApiParameter(
            name='token',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Token reçu par email"
        ),
    ],
    responses={
        200: OpenApiResponse(description="Mot de passe changé avec succès"),
        400: OpenApiResponse(description="Token invalide ou expiré"),
    },
)
class ConfirmPasswordChangeView(APIView):
    permission_classes = []

    def get(self, request):
        token = request.query_params.get('token')

        if not token:
            return Response(
                {"error": "Token manquant."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            change_request = PasswordChangeRequest.objects.get(
                token=token,
                is_used=False
            )
        except PasswordChangeRequest.DoesNotExist:
            return Response(
                {"error": "Lien invalide."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if change_request.is_expired:
            change_request.delete()
            return Response(
                {"error": "Ce lien a expiré. Veuillez refaire la demande."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Appliquer le nouveau mot de passe hashé
        user          = change_request.user
        user.password = change_request.new_password_hash
        user.password_changed = True
        user.save(update_fields=['password', 'password_changed'])

        # ✅ Marquer la demande comme utilisée
        change_request.is_used = True
        change_request.save(update_fields=['is_used'])

        return Response(
            {"message": "Mot de passe changé avec succès. Vous pouvez vous reconnecter."},
            status=status.HTTP_200_OK
        )