from rest_framework import serializers
from .models import Payment, Refund, AuditLog
from django.contrib.auth.models import User

class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for Payment model - converts to/from JSON
    """
    class Meta:
        model = Payment
        fields = [
            'id', 
            'idempotency_key', 
            'user', 
            'amount', 
            'currency', 
            'status', 
            'description', 
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreatePaymentSerializer(serializers.Serializer):
    """
    Serializer for creating payments with validation
    """
    idempotency_key = serializers.CharField(max_length=255)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3, default='USD')
    description = serializers.CharField(required=False, allow_blank=True)
    
    def validate_amount(self, value):
        """Custom validation for amount"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        if value > 1000000:
            raise serializers.ValidationError("Amount exceeds maximum limit")
        return value
    
    def validate_idempotency_key(self, value):
        """Ensure idempotency key is not empty"""
        if not value or value.strip() == '':
            raise serializers.ValidationError("Idempotency key cannot be empty")
        return value.strip()


class RefundSerializer(serializers.ModelSerializer):
    """
    Serializer for Refund model
    """
    payment_id = serializers.UUIDField(source='payment.id', read_only=True)
    
    class Meta:
        model = Refund
        fields = ['id', 'payment_id', 'amount', 'reason', 'status', 'created_at']
        read_only_fields = ['id', 'created_at', 'status']


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for AuditLog - read-only
    """
    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'details', 'user', 'timestamp']
        read_only_fields = ['id', 'action', 'details', 'user', 'timestamp']