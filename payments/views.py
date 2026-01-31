from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.contrib.auth.models import User 
from .models import Payment, Refund, AuditLog
from decimal import Decimal
from .serializers import (
    PaymentSerializer, 
    CreatePaymentSerializer, 
    RefundSerializer,
    AuditLogSerializer
)

def index(request):
    return render(request, 'payments/index.html')
    
class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Payment CRUD operations
    Handles idempotency, refunds, and audit logging
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    
    @transaction.atomic
    def create(self, request):
        """
        Create payment with idempotency check
        
        If payment with same idempotency_key exists, return existing payment
        Otherwise create new payment
        """
        serializer = CreatePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        idempotency_key = serializer.validated_data['idempotency_key']
        
        # Check for existing payment with same idempotency key
        existing_payment = Payment.objects.filter(
            idempotency_key=idempotency_key
        ).first()
        
        if existing_payment:
            # Return existing payment (idempotent!)
            return Response(
                PaymentSerializer(existing_payment).data,
                status=status.HTTP_200_OK
            )

        # Get or create default user for testing
        default_user, _ = User.objects.get_or_create(
            username='api_user',
            defaults={
                'email': 'api@example.com',
                'is_active': True
            }
        )
                # Create new payment
        payment = Payment.objects.create(
            user=default_user,
            idempotency_key=idempotency_key,
            amount=serializer.validated_data['amount'],
            currency=serializer.validated_data.get('currency', 'USD'),
            description=serializer.validated_data.get('description', ''),
            status='COMPLETED'  # Simulate immediate success
        )
        
        # Create audit log
        AuditLog.objects.create(
            payment=payment,
            action='PAYMENT_CREATED',
            details={
                'amount': float(payment.amount),
                'currency': payment.currency,
                'idempotency_key': idempotency_key
            },
            user=default_user
        )
        
        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def refund(self, request, pk=None):
        """
        Custom action: POST /api/payments/{id}/refund/
        
        Refunds a payment (full or partial)
        """
        payment = self.get_object()
        
        # Validation: Can't refund already refunded payment
        if payment.status == 'REFUNDED':
            return Response(
                {'error': 'Payment already refunded'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get refund amount (default to full amount)
        refund_amount_raw = request.data.get('amount', payment.amount)
        refund_amount = Decimal(str(refund_amount_raw))
        reason = request.data.get('reason', 'Customer requested refund')
        
        # Validate refund amount
        if refund_amount > payment.amount:
            return Response(
                {'error': 'Refund amount exceeds payment amount'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create refund record
        refund = Refund.objects.create(
            payment=payment,
            amount=refund_amount,
            reason=reason,
            status='COMPLETED'
        )
        
        # Update payment status
        payment.status = 'REFUNDED'
        payment.save()
        
        # Create audit log
        AuditLog.objects.create(
            payment=payment,
            action='PAYMENT_REFUNDED',
            details={
                'refund_id': str(refund.id),
                'amount': float(refund_amount),
                'reason': reason
            },
            user=None
        )
        
        return Response(
            RefundSerializer(refund).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['get'])
    def my_payments(self, request):
        """
        Custom action: GET /api/payments/my-payments/
        
        Returns current user's payments
        """
        payments = Payment.objects.filter(user=request.user)
        serializer = self.get_serializer(payments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='audit-trail')
    def audit_trail(self, request, pk=None):
        """
        Custom action: GET /api/payments/{id}/audit-trail/
        
        Returns audit logs for a payment
        """
        payment = self.get_object()
        audit_logs = payment.audit_logs.all()
        serializer = AuditLogSerializer(audit_logs, many=True)
        return Response(serializer.data)


class WebhookViewSet(viewsets.ViewSet):
    """
    Simulated webhook endpoint (like Stripe webhooks)
    """
    
    def create(self, request):
        """
        POST /api/webhooks/payment-confirmation/
        
        Simulates receiving payment confirmation from payment provider
        """ 
        
        event_type = request.data.get('event_type')
        payment_id = request.data.get('payment_id')
        
        if event_type == 'payment.succeeded':
            try:
                payment = Payment.objects.get(id=payment_id)
                payment.status = 'COMPLETED'
                payment.save()
                
                AuditLog.objects.create(
                    payment=payment,
                    action='WEBHOOK_RECEIVED',
                    details={'event_type': event_type},
                    user=None
                )
                
                return Response({'status': 'processed'})
            except Payment.DoesNotExist:
                return Response(
                    {'error': 'Payment not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response({'status': 'ignored'})