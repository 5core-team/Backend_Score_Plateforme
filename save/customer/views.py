from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from users.models import ScoreUser
from django.contrib.auth.hashers import make_password
from score.utils import create_file, get_media_url
from score.permissions import IsHuissier, IsPasswordChanged
from score.validators import validate_string, validate_file
from .models import Customer
import uuid
from .serializers import CustomerListSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# class CreateClientView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         user = request.user
#         if user.role != "huissier":
#             return Response({'message': "Seuls les huissiers peuvent créer des clients."}, status=403)

#         first_name = request.data.get('first_name')
#         last_name = request.data.get('last_name')
#         npi = request.data.get('npi')
#         phone = request.data.get('phone')
#         email = request.data.get('email')
#         password = request.data.get('password')

#         if not all([first_name, last_name, npi, phone, email, password]):
#             return Response(
#                 {"error": "Tous les champs sont requis."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         if ScoreUser.objects.filter(username=npi).exists():
#             return Response(
#                 {"error": "Un utilisateur avec ce NPI existe déjà."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         if ScoreUser.objects.filter(email=email).exists():
#             return Response(
#                 {"error": "Un utilisateur avec cet email existe déjà."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         client = ScoreUser.objects.create(
#             username=npi,
#             first_name=first_name,
#             last_name=last_name,
#             phone_number=phone,
#             email=email,
#             role="client",  # ou "particulier" selon ton modèle
#             password=make_password(password),
#             created_by=user  # trace du créateur
#         )

#         return Response(
#             {"message": "Client créé avec succès."},
#             status=status.HTTP_201_CREATED
#         )


# class CreateCustomer(APIView):
#     permission_classes = [IsAuthenticated, IsHuissier, IsPasswordChanged]

#     def post(self, request: Request):
#         user = request.user
#         # Get form
#         first_name = request.data.get("first_name")
#         last_name = request.data.get("last_name")
#         picture = request.FILES.get("picture")
#         npi = request.data.get("npi")
#         phone_number = request.data.get("phone_number")
#         validator = {
#             'required': "Missing field",
#             'length': {
#                 'value': 2,
#                 'message': "This field must have at least 2 characters"
#             },
#             'name': "Invalid format"
#         }
#         number_validator = {
#             'required': "Missing field",
#             'length': {
#                 'value': 6,
#                 'message': "This field must have at least 6 characters"
#             },
#             'number': "Phone must be number" 
#         }
#         print(f"Phone number {phone_number}")
#         # Validate form
#         if not all([first_name, last_name, picture, npi, phone_number]):
#             return Response({
#                 'error': "Fields first_name, last_name, picture, npi, phone_number are required"
#             }, status=400)
#         error = validate_string(npi, validator)
#         if error:
#             return Response({'error': error}, status=400)
#         error = validate_string(last_name, validator)
#         if error:
#             return Response({'error': error}, status=400)
#         error = validate_string(first_name, validator)
#         if error:
#             return Response({'error': error}, status=400)
#         num_error = validate_string(phone_number, number_validator)
#         if (num_error):
#             return Response({
#                 'error': num_error,
#             }, status=400)
#         if (validate_file(picture, [".png", ".jpg", ".jpeg"]) == False):
#             return Response({
#                 'error': "Invalid profile picture format"
#             }, status=400)
#         if Customer.objects.filter(npi=npi, phone_number=phone_number, country=user.huissier.front_office.country).exists():
#             return Response({
#                 'error': "Customer already exists"
#             }, status=400)
#         new_picture = create_file(picture)
#         customer = Customer.objects.create(
#             uuid=str(uuid.uuid4()),
#             first_name=first_name,
#             last_name=last_name,
#             picture=new_picture,
#             npi=npi,
#             phone_number=phone_number,
#             huissier=user.huissier,
#             zone=user.huissier.zone,
#             front_office=user.huissier.front_office,
#             country=user.huissier.front_office.country
#         )
#         customer.save()
#         return Response({
#             'message': "Customer succesfully created"
#         }, status=201)

@method_decorator(csrf_exempt, name='dispatch')
class CreateCustomer(APIView):
    permission_classes = [IsAuthenticated, IsHuissier, IsPasswordChanged]

    def post(self, request: Request):
        user = request.user

        # Récupération des champs
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        npi = request.data.get("npi")
        phone_number = request.data.get("phone_number")
        email = request.data.get("email")

        validator = {
            'required': "Missing field",
            'length': {
                'value': 2,
                'message': "This field must have at least 2 characters"
            },
            'name': "Invalid format"
        }

        number_validator = {
            'required': "Missing field",
            'length': {
                'value': 6,
                'message': "This field must have at least 6 characters"
            },
            'number': "Phone must be number"
        }

        email_validator = {
            'required': "Missing field",
            'length': {
                'value': 5,
                'message': "Email must be valid"
            },
            'email': "Invalid email format"
        }

        # Validation des champs
        if not all([first_name, last_name, npi, phone_number, email]):
            return Response({
                'error': "Fields first_name, last_name, npi, phone_number, email are required"
            }, status=400)

        for field_name, field_value, rules in [
            ("npi", npi, validator),
            ("last_name", last_name, validator),
            ("first_name", first_name, validator),
            ("phone_number", phone_number, number_validator),
            ("email", email, email_validator)
        ]:
            error = validate_string(field_value, rules)
            if error:
                return Response({'error': f"{field_name}: {error}"}, status=400)

        # Vérification d'existence
        if Customer.objects.filter(npi=npi, phone_number=phone_number, country=user.huissier.front_office.country).exists():
            return Response({'error': "Customer already exists"}, status=400)

        # Création du client
        customer = Customer.objects.create(
            uuid=str(uuid.uuid4()),
            first_name=first_name,
            last_name=last_name,
            npi=npi,
            phone_number=phone_number,
            email=email,
            huissier=user.huissier,
            zone=user.huissier.zone,
            front_office=user.huissier.front_office,
            country=user.huissier.front_office.country
        )
        return Response({'message': "Customer successfully created"}, status=201)

class CustomerByNPI(APIView):
    permission_classes = [IsAuthenticated, IsHuissier, IsPasswordChanged]

    def get(self, request: Request):
        npi = request.GET.get("npi")
        if (not npi):
            return Response({
                'error': "npi required"
            }, status=400)
        if (not isinstance(npi, str)):
            return Response({
                'error': "invalid npi"
            }, status=400)
        try:
            customer = Customer.objects.get(npi=npi)
        except Customer.DoesNotExist:
            return Response({
                'error': 'customer not found'
            }, status=404)
        return Response({
            'customer': customer.first_name + " " + customer.last_name
        }, status=200)

@method_decorator(csrf_exempt, name='dispatch')
class CustomersList(APIView):
    permission_classes = [IsAuthenticated, IsHuissier, IsPasswordChanged]

    def get(self, request: Request):
        user = request.user
        customers = Customer.objects.filter(country=user.huissier.front_office.country)
        return Response({
            'customers': CustomerListSerializer(customers, many=True).data
        }, status=200)
    
