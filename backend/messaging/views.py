from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q
from .models import Message
from .serializers import MessageSerializer
from donations.models import Donation


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def donation_messages(request, donation_id):
    """List or send messages for a specific donation."""
    try:
        donation = Donation.objects.get(id=donation_id)
    except Donation.DoesNotExist:
        return Response({'error': 'Donation not found'}, status=status.HTTP_404_NOT_FOUND)

    # Security: only donor or acceptor can access
    user = request.user
    if user != donation.donor and user != donation.acceptor and user != donation.ai_suggested_acceptor:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        messages = Message.objects.filter(donation=donation)
        # Mark as read for current user
        messages.exclude(sender=user).filter(is_read=False).update(is_read=True)
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = MessageSerializer(data={**request.data, 'donation': donation_id})
        if serializer.is_valid():
            serializer.save(sender=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unread_count(request):
    """Get count of unread messages for current user."""
    count = Message.objects.filter(
        donation__in=Donation.objects.filter(
            Q(donor=request.user) | Q(acceptor=request.user) | Q(ai_suggested_acceptor=request.user)
        ),
        is_read=False,
    ).exclude(sender=request.user).count()

    return Response({'unread_count': count})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def per_donation_unread(request):
    """Get unread message counts grouped by donation for current user."""
    from django.db.models import Count

    user_donations = Donation.objects.filter(
        Q(donor=request.user) | Q(acceptor=request.user) | Q(ai_suggested_acceptor=request.user)
    )

    counts = (
        Message.objects.filter(donation__in=user_donations, is_read=False)
        .exclude(sender=request.user)
        .values('donation_id')
        .annotate(count=Count('id'))
    )

    result = {item['donation_id']: item['count'] for item in counts}
    return Response(result)
