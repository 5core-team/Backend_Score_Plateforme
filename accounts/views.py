from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.request import Request

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth import authenticate
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .serializers import UserProfileSerializer
from .models import ScoreUser



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import AccountCredentials, ScoreUser  # ton modèle utilisateur


@method_decorator(csrf_exempt, name='dispatch')
# class Login(APIView):
#     """
#     Dette technique: Considérer les comptes non actifs
#     """
#     def post(self, request):
#         email = request.data.get("email")
#         password = request.data.get("password")

#         if not email or not password:
#             return Response({"Error_message": "incorrect email or password"}, status=400)

#         user = get_object_or_404(ScoreUser, email=email)

#         if not user.check_password(password):
#             return Response({"Error_message": "Bad password"}, status=400)

#         # Création des tokens
#         refresh_token = RefreshToken.for_user(user)
#         access_token = str(refresh_token.access_token)

#         return Response({
#             "access_token": access_token,
#             "refresh_token": str(refresh_token),
#             "type_user": user.role
#         }, status=200)


class Login(APIView):
    """
    Authentification utilisateur sécurisée
    """

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=email, password=password)

        if not user:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.is_active:
            return Response(
                {"error": "Account is inactive"},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "type_user": user.role
        }, status=status.HTTP_200_OK)


class VerifyPasswordSetupCredentials(APIView):
    """
    Vue GET pour vérifier si le token de setup du compte est valide.
    Paramètres GET: uid, token
    """

    def get(self, request):
        uid = request.query_params.get("uid")
        token = request.query_params.get("token")

        if not uid or not token:
            return Response({"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = get_object_or_404(ScoreUser, pk=user_id)
        except Exception:
            return Response({"error": "Invalid uid"}, status=status.HTTP_400_BAD_REQUEST)

        # Récupération des credentials
        try:
            account_cred = AccountCredentials.objects.get(user=user, token=token)
        except AccountCredentials.DoesNotExist:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

        # Vérification de l'expiration
        if account_cred.expiry_date < timezone.now():
            return Response({"error": "Token expired"}, status=status.HTTP_400_BAD_REQUEST)

        # Si tout est OK
        return Response({"msg": "Token is valid"}, status=status.HTTP_200_OK)



class PasswordSetup():
    """
    Vue avec méthode POST
    Paramètres: uid, token et password
    Logique: Cette vue set un mot de passe au compte lorsque les credentials sont valides.
    """
    pass

class PasswordResetCode():
    """
    Vue avec une méthode POST
    Paramètres: email
    Logique: Obtenir un code de validation pour la rénitialisation du mot de passe (utile pour mot de passe oublié)
    Contraintes:
        - Délai entre génération de code est de 90s
        - Pas plus de 4 tentatives dans la journée
    """
    pass

class VerifyValidationCode():
    """
    Vue avec méthode POST
    Paramètres: email, code (reçu par mail)
    Logique: Vérifier le code reçu par mail pour la rénitialisation de mot de passe et retourner un token
        qui expire sur une durée déterminée
    Contraintes:
        - La durée de validité du token doit être configurable
        - Une fois utilisé le token est invalide
    """
    pass

class ResetPassword():
    """
    Vue avec une méthode POST
    Paramètres: token et password
    Logique: Vérifier la validité du token et rénitialiser le mot de passe
    """
    pass

@method_decorator(csrf_exempt, name='dispatch')
class ChangePassword(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request):
        user = request.user

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

        return Response(
            {"message": "Mot de passe modifié avec succès."},
            status=status.HTTP_200_OK
        )


class ProfileView(generics.UpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user