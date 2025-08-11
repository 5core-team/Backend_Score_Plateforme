from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from dateutil.relativedelta import relativedelta
from users.models import ScoreUser
from users.serializers import ScoreUserSerializer
from country.models import Country, Subscription
from .utils import generate_random_password
from rest_framework.request import Request
from django.utils.timezone import now
from country.serializers import CountrySerializer
from .serializers import SubscriptionSerializer
from score.permissions import IsScoreAdmin, IsHuissier
from customer.models import Customer, Loan

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import CustomerSerializer
from customer.serializers import CustomerListSerializer

from .serializers import LoanSerializer
from django.core.mail import send_mail
from datetime import date

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

@method_decorator(csrf_exempt, name='dispatch')
class Login(APIView):
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

@method_decorator(csrf_exempt, name='dispatch')
class NewCountry(APIView):
    permission_classes = [IsAuthenticated, IsScoreAdmin] # Permet de vérifier si l'utilisateur est connecté
    def post(self, request):
        user = request.user
        name = request.data.get('name')
        country_code = request.data.get('country_code')
        phone_code = request.data.get('phone_code')
        email = request.data.get('email')

        if not all([country_code, phone_code, email, name]):
            return Response(
                {"error": "Tous les champs (country_code, phone_code, email, name) sont requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if Country.objects.filter(country_code=country_code, name=name).exists():
            return Response(
                {"error": f"Le pays avec le code '{country_code}' existe déjà."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create user if it doesn't exist
        users = ScoreUser.objects.filter(email=email)
        if users.exists():
            return Response({
                'error': "Email already taken"
            }, status=400)
        user = ScoreUser()
        user.email = email
        user.username = name
        user.role = "country"
        password = generate_random_password()
        user.set_password(password)
        user.save()
        
        country = Country.objects.create(
            country_code=country_code,
            phone_code=phone_code,
            name=name,
            user=user  # Liaison du pays à l'utilisateur
        )
        country.save()

        return Response(
            {"message": "Pays créé avec succès.", "password": password},
            status=status.HTTP_201_CREATED
        )


@method_decorator(csrf_exempt, name='dispatch')
class CountrySubscribe(APIView):
    permission_classes = [IsAuthenticated, IsScoreAdmin]

    def post(self, request: Request):
        user = request.user
        plan = request.data.get("plan")
        name = request.data.get("name")
        # Check country
        countries = Country.objects.filter(name=name)
        if (not countries.exists()):
            return Response({
                'error': "Country not found"
            }, status=404)
        country = countries[0]
        # Check plan
        if plan not in ["monthly", "annual"]:
            return Response({'error': "Invalid plan"}, status=400)
        actives = country.subscriptions.filter(expires_in__gt=now())
        target = now()
        if (actives.exists()):
            target = actives.order_by("-expires_in").first().expires_in
        if (plan == "monthly"):
            end_date = target + relativedelta(months=1)
        elif (plan == "annual"):
            end_date = target + relativedelta(years=1)
        subscription = Subscription()
        subscription.country = country
        subscription.expires_in = end_date
        subscription.save()

        return Response({
            'message': "Subscription added"
        }, status=201)
    
@method_decorator(csrf_exempt, name='dispatch')
class CountryData(APIView):
    permission_classes = [IsAuthenticated, IsScoreAdmin]

    def get(self, request: Request, country_name: str):
        user = request.user
        try:
            country = Country.objects.get(name=country_name)
        except Country.DoesNotExist:
            return Response({
                'error': "Country not found"
            }, status=status.HTTP_404_NOT_FOUND)
        parsed_country = CountrySerializer(country).data

        return Response({
            'country': parsed_country
        }, status=200)
    

@method_decorator(csrf_exempt, name='dispatch')
class CountrySubscriptions(APIView):
    permission_classes = [IsAuthenticated, IsScoreAdmin]

    def get(self, request: Request, country_name: str):
        if (not country_name):
            return Response({
                'error': "Country name required"
            }, status=400)
        try:
            country = Country.objects.get(name=country_name)
        except Country.DoesNotExist:
            return Response({
                'error': "Country not found"
            }, status=404)
        parsed_subs = SubscriptionSerializer(country.subscriptions, many=True).data
        return Response({
            'subscriptions': parsed_subs
        }, status=200)
    


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
    

@method_decorator(csrf_exempt, name='dispatch')
class CountryListView(APIView):
    permission_classes = [IsAuthenticated, IsScoreAdmin]

    def get(self, request):
        countries = Country.objects.all()
        serializer = CountrySerializer(countries, many=True)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class HuissierCustomerListView(APIView):
    permission_classes = [IsAuthenticated, IsHuissier]

    def get(self, request):
        user = request.user

        # Suppose que le modèle Huissier est lié à User via OneToOne
        huissier = getattr(user, "huissier", None)
        if not huissier:
            return Response({"detail": "Vous n'êtes pas un huissier."}, status=403)

        customers = Customer.objects.filter(huissier=huissier)
        serializer = CustomerListSerializer(customers, many=True)
        return Response({
            'customers': serializer.data
        })


@method_decorator(csrf_exempt, name='dispatch')
class CustomerLoanDetailView(APIView):
    permission_classes = [IsAuthenticated, IsHuissier]

    def get(self, request, customer_id):
        user = request.user
        huissier = getattr(user, "huissier", None)

        try:
            customer = Customer.objects.get(uuid=customer_id)
        except Customer.DoesNotExist:
            return Response({
                'error': "Customer not found"
            }, status=404)
        # customer = get_object_or_404(Customer, id=customer_id)

        if customer.huissier != huissier:
            return Response({"detail": "Non autorisé"}, status=403)

        loans = Loan.objects.filter(customer=customer)
        serializer = LoanSerializer(loans, many=True)
        return Response({
            'customer': CustomerSerializer(customer).data,
            'loans': serializer.data
        })

@method_decorator(csrf_exempt, name='dispatch')
class HuissierAlertsView(APIView):
    permission_classes = [IsAuthenticated, IsHuissier]

    def get(self, request):
        user = request.user
        huissier = getattr(user, "huissier", None)

        loans = Loan.objects.filter(
            customer__huissier=huissier,
            deadline__lt=date.today(),
        ).exclude(status="done")

        serializer = LoanSerializer(loans, many=True)
        return Response({
            "alerts": serializer.data,
            "total_alerts": loans.count()
        })


@method_decorator(csrf_exempt, name='dispatch')
class ZoneCustomerListView(APIView):
    permission_classes = [IsAuthenticated, IsHuissier]

    def get(self, request):
        user = request.user
        huissier = getattr(user, "huissier", None)
        zone = huissier.zone

        customers = Customer.objects.filter(zone=zone)
        serializer = CustomerSerializer(customers, many=True)
        return Response({
            'customers': serializer.data
        })
@method_decorator(csrf_exempt, name='dispatch')
class SendEm(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        send_mail(
            subject='Juste un test',
            message="C'est juste un contenu de test",
            from_email="hannieldegbelo@gmail.com",
            recipient_list=["horuskoeus6@gmail.com"],
            fail_silently=False
        )
        return Response({
            'message': "Successfully sended"
        })


# class CountryUserListView(generics.ListAPIView):
#     queryset = User.objects.filter(role='country')
#     serializer_class = UserSerializer
#     permission_classes = [IsAuthenticated]



# class FrontOfficeListView(generics.ListAPIView):
#     queryset = User.objects.filter(role='front_office')
#     serializer_class = UserSerializer
#     permission_classes = [IsAuthenticated]



# class ConseillerListView(generics.ListAPIView):
#     queryset = User.objects.filter(role='conseiller')
#     serializer_class = UserSerializer
#     permission_classes = [IsAuthenticated]

    

# class HuissierListView(generics.ListAPIView):
#     queryset = User.objects.filter(role='huissier')
#     serializer_class = UserSerializer
#     permission_classes = [IsAuthenticated]
