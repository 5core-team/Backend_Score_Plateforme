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


from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .serializers import UserProfileSerializer
from .models import ScoreUser

@method_decorator(csrf_exempt, name='dispatch')
class Login(APIView):
    """
    Dette technique: Considérer les comptes non actifs
    """
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"Error_message": "incorrect email or password"}, status=400)

        user = get_object_or_404(ScoreUser, email=email)

        if not user.check_password(password):
            return Response({"Error_message": "Bad password"}, status=400)

        # Création des tokens
        refresh_token = RefreshToken.for_user(user)
        access_token = str(refresh_token.access_token)

        return Response({
            "access_token": access_token,
            "refresh_token": str(refresh_token),
            "type_user": user.role
        }, status=200)

class VerifyPasswordSetupCredentials():
    """
    Vue avec une méthode GET
    Paramètres: uid (userId) et token
    Logique: Cette vue vérifie si le token n'est pas encore expiré.
        Utiliser le modèle AccountCredentials
    """
    pass

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