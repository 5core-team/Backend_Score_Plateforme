# from rest_framework import serializers
# from .models import ScoreUser
# from country.models import Subscription

# class ScoreUserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ScoreUser
#         fields = ['username', 'email', 'role', 'password']
#         extra_kwargs = {
#             'password': {'write_only': True}
#         }

#     def create(self, validated_data):
#         user = ScoreUser(
#             username=validated_data['username'],
#             email=validated_data['email'],
#             role=validated_data['role']
#         )
#         user.set_password(validated_data['password'])
#         user.save()
#         return user

# class SubscriptionSerializer(serializers.ModelSerializer):
#     is_active = serializers.SerializerMethodField()
#     class Meta:
#         model = Subscription
#         fields = ['created_at', 'expires_in', 'is_active']
#     def get_is_active(self, obj):
#         return obj.is_active()


from rest_framework import serializers
from .models import ScoreUser
from country.models import Subscription
from customer.models import Customer, Loan, Repayment


class ScoreUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreUser
        fields = ['username', 'email', 'role', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = ScoreUser(
            username=validated_data['username'],
            email=validated_data['email'],
            role=validated_data['role']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class SubscriptionSerializer(serializers.ModelSerializer):
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ['created_at', 'expires_in', 'is_active']

    def get_is_active(self, obj):
        return obj.is_active()


# === SERIALIZERS SPÉCIFIQUES AU RÔLE HUISSIER ===

class RepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repayment
        fields = ['id', 'date']


class LoanSerializer(serializers.ModelSerializer):
    repayments = RepaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Loan
        fields = [
            'id', 'date', 'amount', 'periodicity', 'rate',
            'deadline_amount', 'deadline', 'solvability', 'status', 'repayments'
        ]


class CustomerSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Customer
        fields = [
            'uuid', 'first_name', 'last_name', 'npi', 'phone_number',
            'credit_score'
        ]
