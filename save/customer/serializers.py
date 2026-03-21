from rest_framework import serializers
from .models import Customer, Loan
from score.utils import FileSerializer

class CreditorNPISerializer(serializers.Field):
    def to_representation(self, value):
        try:
            customer = Customer.objects.get(npi=value)
            return customer.first_name + " " + customer.last_name
        except Customer.DoesNotExist:
            return "Undefined"

class ReceivableCustomerFieldSerializer(serializers.Field):
    def to_representation(self, value: Customer):
        return value.first_name + " " + value.last_name

class LoanSerializer(serializers.ModelSerializer):
    creditor_npi = CreditorNPISerializer()
    class Meta:
        model = Loan
        fields = '__all__'

class ReceivableLoanSerializer(serializers.ModelSerializer):
    customer = ReceivableCustomerFieldSerializer()
    class Meta:
        model = Loan
        fields = ['customer', 'date', 'amount', 'periodicity', 'deadline_amount', 'deadline', 'verified', 'solvability', 'status']

class CustomerListSerializer(serializers.ModelSerializer):
    loans = LoanSerializer(many=True)
    class Meta:
        model = Customer
        fields = ["uuid", "npi", "phone_number", 'loans']
