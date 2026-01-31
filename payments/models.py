from django.db import models
from django.contrib.auth.models import User
import uuid

class Payment(models.Model):
    """
    Payment transaction record with idempotency support
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    # UUID primary key (better for distributed systems)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Idempotency key - prevents duplicate payments
    idempotency_key = models.CharField(
        max_length=255, 
        unique=True, 
        db_index=True,
        help_text="Unique key to prevent duplicate payments"
    )
    
    # Payment details
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='payments'
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Payment amount in USD"
    )
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDING'
    )
    description = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']  # Newest first
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Payment {self.id} - ${self.amount} ({self.status})"


class Refund(models.Model):
    """
    Refund record linked to original payment
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment, 
        on_delete=models.CASCADE, 
        related_name='refunds'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDING'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Refund {self.id} - ${self.amount} for Payment {self.payment.id}"


class AuditLog(models.Model):
    """
    Immutable audit trail for compliance
    """
    payment = models.ForeignKey(
        Payment, 
        on_delete=models.CASCADE, 
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50)
    details = models.JSONField()  # Flexible JSON storage
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        # Make this table append-only (no updates/deletes in app logic)
    
    def __str__(self):
        return f"{self.action} - {self.timestamp}"