from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from users.models import ScoreUser
from customer.models import Customer, Loan
from country.models import FrontOffice, Huissier, Financial, AvailableZone
from django.contrib.auth.hashers import make_password
from score.permissions import IsCountry, IsPasswordChanged, IsFrontOffice, IsHuissier
from users.utils import generate_random_password
from score.utils import generate_random_code, send_email
# from django.core.cache import cache
from django.conf import settings
import redis
from customer.serializers import CustomerListSerializer, LoanSerializer, ReceivableLoanSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .serializers import ZoneSerializer

cache = redis.StrictRedis(host='localhost', port=6379, db=0)

@method_decorator(csrf_exempt, name='dispatch')
class CreateFrontOffice(APIView):
    permission_classes = [IsAuthenticated, IsCountry, IsPasswordChanged]

    def post(self, request: Request):
        user = request.user
        country = user.country
        name = request.data.get('front_office_name')
        username = request.data.get('username')
        npi = request.data.get('npi')
        phone = request.data.get('phone')
        email = request.data.get('email')
        # localisation = request.data.get('localisation')
        password = generate_random_password()

        if not all([name, username, npi, phone, email]):
            return Response(
                {"error": "Tous les champs (front_office_name, username, npi, phone, email) sont requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if ScoreUser.objects.filter(username=username, email=email).exists():
            return Response({"error": "Un utilisateur avec ce NPI existe déjà."}, status=400)
        if FrontOffice.objects.filter(name=name, npi=npi, phone=phone, country=country).exists():
            return Response({"error": "Ce front office existe déjà"}, status=400)

        new_user = ScoreUser.objects.create(
            username=username,
            email=email,
            role="front office",
            password=make_password(password),
        )
        new_user.save()
        office = FrontOffice()
        office.name = name
        # office.localisation = localisation
        office.npi = npi
        office.phone = phone
        office.country = country
        office.user = new_user
        office.save()

        return Response({"message": "Front-office créé avec succès.", 'password': password}, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class CreateHuissier(APIView):
    permission_classes = [IsAuthenticated, IsFrontOffice, IsPasswordChanged]

    def post(self, request):
        user = request.user
        
        username = request.data.get('username')
        npi = request.data.get('npi')
        phone = request.data.get('phone')
        email = request.data.get('email')
        zone = request.data.get('zone')
        password = generate_random_password()

        if not all([username, npi, phone, email, password, zone]):
            return Response(
                {"error": "Tous les champs (username, npi, phone, email, zone) sont requis."},
                status=400
            )

        if ScoreUser.objects.filter(username=username, email=email).exists():
            return Response({"error": "Ce utilisateur existe déjà."}, status=400)
        if (AvailableZone.objects.filter(name=zone, front_office=user.frontoffice).exists() == False):
            return Response({
                'error': "Invalid zone"
            }, status=400)
        if Huissier.objects.filter(npi=npi).exists():
            return Response({"error": "Un utilisateur avec cet npi existe déjà."}, status=400)
        new_user = ScoreUser.objects.create(
            username=username,
            email=email,
            role="huissier",
            password=make_password(password),
        )
        new_user.save()

        huissier = Huissier.objects.create(
            user=new_user,
            front_office=user.frontoffice,
            phone=phone,
            npi=npi,
        )
        huissier.save()

        return Response({"message": "Huissier créé avec succès.", 'password': password}, status=201)

@method_decorator(csrf_exempt, name='dispatch')
class AddZone(APIView):
    permission_classes = [IsAuthenticated, IsFrontOffice, IsPasswordChanged]

    def post(self, request: Request):
        user = request.user
        name = request.data.get("name")
        if (not all([name])):
            return Response({
                'error': "Les champs name & localisation sont requis"
            }, status=400)
        if (AvailableZone.objects.filter(name=name, front_office=user.frontoffice).exists()):
            return Response({
                'error': "This zone already exists"
            }, status=400)
        AvailableZone.objects.create(
            name=name,
            front_office=user.frontoffice
        )
        return Response({
            'message': "Zone added"
        }, status=200)

class Zones(APIView):
    permission_classes = [IsAuthenticated, IsFrontOffice, IsPasswordChanged]

    def get(self, request: Request):
        user = request.user
        zone = AvailableZone.objects.filter(front_office=user.frontoffice)
        return Response({
            'zones': ZoneSerializer(zone, many=True).data
        })


@method_decorator(csrf_exempt, name='dispatch')
class RemoveZone(APIView):
    permission_classes = [IsAuthenticated, IsFrontOffice, IsPasswordChanged]

    def post(self, request: Request):
        user = request.user
        name = request.data.get("name")
        if not name:
            return Response({
                'error': "Le champs name est requis"
            }, status=400)
        try:
            zone = AvailableZone.objects.get(name=name, front_office=user.frontoffice)
        except AvailableZone.DoesNotExist:
            return Response({
                'error': "Zone not found"
            }, status=404)
        zone.delete()
        return Response({
            'message': "Successfully deleted"
        })

@method_decorator(csrf_exempt, name='dispatch')
class CreateConseillerFinancier(APIView):
    permission_classes = [IsAuthenticated, IsFrontOffice, IsPasswordChanged]

    def post(self, request):
        user = request.user
        
        username = request.data.get("username")
        email = request.data.get('email')
        password = generate_random_password()
        name = request.data.get("name")
        phone = request.data.get('phone')
        npi = request.data.get('npi')

        if not all([username, name, npi, phone, email]):
            return Response(
                {"error": "Tous les champs (username, name, npi, phone, email) sont requis."},
                status=400
            )

        if ScoreUser.objects.filter(username=username, email=email).exists():
            return Response({"error": "Ce utilisateur existe déjà."}, status=400)
        if Financial.objects.filter(npi=npi, name=name).exists():
            return Response({"error": "Ce conseiller financier existe déjà."}, status=400)
        new_user = ScoreUser.objects.create(
            email=email,
            username=username,
            password=make_password(password),
            role="conseiller"
        )

        Financial.objects.create(
            user=new_user,
            front_office=user.frontoffice,
            name=name,
            phone=phone,
            npi=npi,
        )
        return Response({"message": "Conseiller financier créé avec succès.", 'password': password}, status=201)

@method_decorator(csrf_exempt, name='dispatch')
class ConsultCustomerAccount(APIView):
    permission_classes = [IsAuthenticated, IsHuissier]

    def post(self, request):
        npi = request.data.get("npi")
        document_number = request.data.get("document_number")

        if not npi or not document_number:
            return Response({
                "error": "Fields 'npi' and 'document_number' are required."
            }, status=400)

        # Vérifie que le client existe dans la base de données
        try:
            customer = Customer.objects.get(npi=npi)
        except Customer.DoesNotExist:
            return Response({
                "error": "No customer found with the given NPI."
            }, status=404)

        # Génère un code unique aléatoire
        unique_code = generate_random_code()
        while (cache.get(unique_code) != None):
            unique_code = generate_random_code()
        cache.set(unique_code, npi, ex=settings.DATA_TIMEOUT)
        data = {
            'subject': "Code de consultation",
            'message': f"Votre code de consultation de compte: {unique_code}",
            'to': customer.email
        }
        send_email(data)
        return Response({
            "message": "Code successfully generated"
        }, status=200)

@method_decorator(csrf_exempt, name='dispatch')
class CheckConsultationCode(APIView):
    permission_classes = [IsAuthenticated, IsHuissier]

    def get(self, request: Request):
        code = request.GET.get('code')
        npi = cache.get(code).decode()
        if not npi:
            return Response({
                'error': "Invalid code"
            }, status=400)
        try:
            customer = Customer.objects.get(npi=npi)
        except Customer.DoesNotExist:
            return Response({
                'error': "Invalid code"
            }, status=400)
        receivables = Loan.objects.filter(creditor_npi=customer.npi)
        parsed_customer = CustomerListSerializer(customer).data
        parsed_customer["receivables"] = ReceivableLoanSerializer(receivables, many=True).data
        return Response({
            'customer': parsed_customer
        }, status=200)

@method_decorator(csrf_exempt, name='dispatch')
class RegisterLoanCode(APIView):
    permission_classes = [IsAuthenticated, IsHuissier]

    def post(self, request: Request):
        npi = request.data.get('npi')
        if (not npi):
            return Response({
                'error': "npi required"
            }, status=400)
        try:
            customer = Customer.objects.get(npi=npi)
        except Customer.DoesNotExist:
            return Response({
                'error': "customer not found"
            }, status=404)
        # Génère un code unique aléatoire
        unique_code = generate_random_code()
        while (cache.get(unique_code)):
            unique_code = generate_random_code()
        cache.set(unique_code, npi, ex=settings.DATA_TIMEOUT)
        data = {
            'subject': "Code d'enregistrement de dette",
            'message': f"Votre code d'enregistrement de dette: {unique_code}",
            'to': customer.email
        }
        send_email(data)
        return Response({
            "message": "Code successfully generated"
        }, status=200)

@method_decorator(csrf_exempt, name='dispatch')
class RegisterLoan(APIView):
    permission_classes = [IsAuthenticated, IsHuissier]

    def post(self, request: Request):
        code = request.data.get("code")
        amount = request.data.get("amount")
        periodicity = request.data.get("periodicity")
        deadline_amount = request.data.get("deadline_amount")
        deadline = request.data.get("deadline")
        creditor_npi = request.data.get("creditor_npi")
        if (not all([code, amount, periodicity, deadline_amount, deadline, creditor_npi])):
            return Response({
                'error': "Fields required (code, amount, periodicity, deadline_amount, deadline)"
            }, status=400)
        if (not periodicity in ["daily", "weekly", "monthly", "quarterly", "biannual", "annual"]):
            return Response({
                'error': "Invalid periodicity field"
            }, status=400)
        try:
            creditor = Customer.objects.get(npi=creditor_npi)
        except Customer.DoesNotExist:
            return Response({
                'error': "Invalid creditor npi"
            }, status=400)
        npi = cache.get(code).decode()
        if (not npi):
            return Response({
                'error': "code expired"
            }, status=400)
        try:
            customer = Customer.objects.get(npi=npi)
        except Customer.DoesNotExist:
            return Response({
                'error': "customer not found"
            }, status=404)
        if (customer == creditor):
            return Response({
                'error': "Invalid creditor npi"
            }, status=400)
        Loan.objects.create(
            amount=amount,
            periodicity=periodicity,
            deadline_amount=deadline_amount,
            deadline=deadline,
            customer=customer,
            creditor_npi=creditor_npi
        )
        return Response({
            'message': "loan successfully registered"
        })

