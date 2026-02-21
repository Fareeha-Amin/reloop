from rest_framework import serializers
from .models import Payment, Commission


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments."""
    donor_name = serializers.CharField(source='user.username', read_only=True)
    donation_id = serializers.IntegerField(source='donation.id', read_only=True)
    
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['user', 'transaction_id', 'status', 'gateway_response']


class PaymentInitiateSerializer(serializers.Serializer):
    """Serializer for initiating payment."""
    donation_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.CharField(default='Card')


class CommissionSerializer(serializers.ModelSerializer):
    """Serializer for commission records."""
    payment_transaction_id = serializers.CharField(source='payment.transaction_id', read_only=True)
    
    class Meta:
        model = Commission
        fields = '__all__'
