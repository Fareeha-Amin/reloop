from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .models import Payment, Commission
from .serializers import PaymentSerializer, PaymentInitiateSerializer, CommissionSerializer
from donations.models import Donation
from logistics.models import PickupRequest
import uuid
from datetime import datetime


class PaymentListView(generics.ListAPIView):
    """List all payments."""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Payment.objects.all()
        return Payment.objects.filter(user=user)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def initiate_payment(request):
    """Initiate a simulated payment."""
    serializer = PaymentInitiateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    donation_id = serializer.validated_data['donation_id']
    amount = serializer.validated_data['amount']
    payment_method = serializer.validated_data['payment_method']
    
    try:
        donation = Donation.objects.get(id=donation_id)
    except Donation.DoesNotExist:
        return Response({'error': 'Donation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user is the donor
    if donation.donor != request.user:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get pickup request to calculate costs
    try:
        pickup_request = PickupRequest.objects.get(donation=donation)
        logistics_cost = pickup_request.total_cost or 0
        platform_commission = pickup_request.platform_commission or 0
    except PickupRequest.DoesNotExist:
        logistics_cost = 0
        platform_commission = 0
    
    # Create payment
    payment = Payment.objects.create(
        user=request.user,
        donation=donation,
        amount=amount,
        platform_commission=platform_commission,
        logistics_cost=logistics_cost,
        payment_method=payment_method,
        transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
        status='PENDING'
    )
    
    return Response({
        'payment_id': payment.id,
        'transaction_id': payment.transaction_id,
        'amount': float(payment.amount),
        'status': payment.status,
        'message': 'Payment initiated. Proceed to checkout.'
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def complete_payment(request, payment_id):
    """Complete a simulated payment (auto-success)."""
    try:
        payment = Payment.objects.get(id=payment_id, user=request.user)
    except Payment.DoesNotExist:
        return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if payment.status != 'PENDING':
        return Response({'error': 'Payment already processed'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Simulate successful payment
    payment.status = 'SUCCESS'
    payment.gateway_response = {
        'status': 'success',
        'message': 'Payment completed successfully',
        'timestamp': datetime.now().isoformat(),
        'simulated': True
    }
    payment.save()
    
    # Create commission record
    Commission.objects.create(
        payment=payment,
        amount=payment.platform_commission,
        percentage=10.0,  # Default commission percentage
        month=datetime.now().month,
        year=datetime.now().year
    )
    
    # Update donation status
    donation = payment.donation
    donation.status = 'PICKUP_SCHEDULED'
    donation.save()
    
    # Update pickup request status
    try:
        pickup_request = PickupRequest.objects.get(donation=donation)
        pickup_request.status = 'SCHEDULED'
        pickup_request.save()
    except PickupRequest.DoesNotExist:
        pass
    
    return Response({
        'payment_id': payment.id,
        'transaction_id': payment.transaction_id,
        'status': payment.status,
        'message': 'Payment successful!',
        'donation_status': donation.status
    })


class CommissionListView(generics.ListAPIView):
    """List all commissions (Admin only)."""
    serializer_class = CommissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role != 'ADMIN':
            return Commission.objects.none()
        return Commission.objects.all()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def commission_summary(request):
    """Get commission summary (Admin only)."""
    if request.user.role != 'ADMIN':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    from django.db.models import Sum, Count
    
    total_commission = Commission.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_payments = Payment.objects.filter(status='SUCCESS').count()
    total_amount = Payment.objects.filter(status='SUCCESS').aggregate(total=Sum('amount'))['total'] or 0
    
    return Response({
        'total_commission': float(total_commission),
        'total_payments': total_payments,
        'total_transaction_amount': float(total_amount),
    })
