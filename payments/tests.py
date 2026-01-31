from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from .models import Payment, Refund, AuditLog

class PaymentAPITestCase(TestCase):
    """
    Test suite for Payment API
    """
    
    def setUp(self):
        """
        Setup runs before EACH test
        Creates test user and API client
        """
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create API client for making requests
        self.client = APIClient()
        
        # Base URL for payments
        self.payments_url = '/api/payments/'
    
    def tearDown(self):
        """
        Cleanup after each test (optional)
        Django auto-deletes test database
        """
        pass
    
    def test_create_payment_success(self):
        """
        Test: Create payment successfully
        """
        data = {
            'idempotency_key': 'test-001',
            'amount': '100.50',
            'currency': 'USD',
            'description': 'Test payment'
        }
        
        response = self.client.post(self.payments_url, data, format='json')
        
        # Assert response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['amount'], '100.50')
        self.assertEqual(response.data['status'], 'COMPLETED')
        self.assertEqual(response.data['idempotency_key'], 'test-001')
        
        # Assert database record created
        self.assertEqual(Payment.objects.count(), 1)
        payment = Payment.objects.first()
        self.assertEqual(payment.amount, Decimal('100.50'))
        
        # Assert audit log created
        self.assertEqual(AuditLog.objects.count(), 1)
        audit = AuditLog.objects.first()
        self.assertEqual(audit.action, 'PAYMENT_CREATED')
    
    def test_idempotency_prevents_duplicates(self):
        """
        Test: Same idempotency key returns existing payment
        """
        data = {
            'idempotency_key': 'duplicate-test',
            'amount': '200.00'
        }
        
        # First request - creates payment
        response1 = self.client.post(self.payments_url, data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        payment_id_1 = response1.data['id']
        
        # Second request - same idempotency key
        response2 = self.client.post(self.payments_url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)  # 200, not 201!
        payment_id_2 = response2.data['id']
        
        # Assert: Same payment returned
        self.assertEqual(payment_id_1, payment_id_2)
        
        # Assert: Only 1 payment in database
        self.assertEqual(Payment.objects.count(), 1)
    
    def test_create_payment_invalid_amount(self):
        """
        Test: Negative amount is rejected
        """
        data = {
            'idempotency_key': 'negative-test',
            'amount': '-50.00'
        }
        
        response = self.client.post(self.payments_url, data, format='json')
        
        # Should fail validation
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', response.data)
        
        # Assert no payment created
        self.assertEqual(Payment.objects.count(), 0)
    
    def test_create_payment_missing_idempotency_key(self):
        """
        Test: Missing idempotency key is rejected
        """
        data = {
            'amount': '100.00'
            # Missing idempotency_key
        }
        
        response = self.client.post(self.payments_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('idempotency_key', response.data)
    
    def test_refund_payment_success(self):
        """
        Test: Refund payment successfully
        """
        # Create payment first
        payment = Payment.objects.create(
            user=self.user,
            idempotency_key='refund-test-001',
            amount=Decimal('300.00'),
            status='COMPLETED'
        )
        
        # Refund it
        refund_url = f'/api/payments/{payment.id}/refund/'
        data = {
            'amount': '100.00',
            'reason': 'Customer request'
        }
        
        response = self.client.post(refund_url, data, format='json')
        
        # Assert response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['amount'], '100.00')
        self.assertEqual(response.data['reason'], 'Customer request')
        
        # Assert refund created in database
        self.assertEqual(Refund.objects.count(), 1)
        refund = Refund.objects.first()
        self.assertEqual(refund.amount, Decimal('100.00'))
        
        # Assert payment status updated
        payment.refresh_from_db()  # Reload from database
        self.assertEqual(payment.status, 'REFUNDED')
        
        # Assert audit log created
        refund_logs = AuditLog.objects.filter(action='PAYMENT_REFUNDED')
        self.assertEqual(refund_logs.count(), 1)
    
    def test_refund_already_refunded_payment(self):
        """
        Test: Cannot refund already refunded payment
        """
        # Create already-refunded payment
        payment = Payment.objects.create(
            user=self.user,
            idempotency_key='already-refunded',
            amount=Decimal('100.00'),
            status='REFUNDED'  # Already refunded!
        )
        
        refund_url = f'/api/payments/{payment.id}/refund/'
        data = {'amount': '50.00', 'reason': 'Test'}
        
        response = self.client.post(refund_url, data, format='json')
        
        # Should be rejected
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already refunded', response.data['error'])
        
        # No new refund created
        self.assertEqual(Refund.objects.count(), 0)
    
    def test_refund_amount_exceeds_payment(self):
        """
        Test: Refund amount cannot exceed payment amount
        """
        payment = Payment.objects.create(
            user=self.user,
            idempotency_key='exceed-test',
            amount=Decimal('100.00'),
            status='COMPLETED'
        )
        
        refund_url = f'/api/payments/{payment.id}/refund/'
        data = {
            'amount': '150.00',  # More than payment!
            'reason': 'Test'
        }
        
        response = self.client.post(refund_url, data, format='json')
        
        # Should be rejected
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('exceeds', response.data['error'])
    
    def test_list_payments(self):
        """
        Test: List all payments
        """
        # Create multiple payments
        Payment.objects.create(
            user=self.user,
            idempotency_key='list-1',
            amount=Decimal('100.00'),
            status='COMPLETED'
        )
        Payment.objects.create(
            user=self.user,
            idempotency_key='list-2',
            amount=Decimal('200.00'),
            status='COMPLETED'
        )
        
        response = self.client.get(self.payments_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_get_payment_detail(self):
        """
        Test: Get single payment details
        """
        payment = Payment.objects.create(
            user=self.user,
            idempotency_key='detail-test',
            amount=Decimal('500.00'),
            status='COMPLETED'
        )
        
        detail_url = f'/api/payments/{payment.id}/'
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(payment.id))
        self.assertEqual(response.data['amount'], '500.00')
    
    def test_audit_trail(self):
        """
        Test: Audit trail shows all payment events
        """
        # Create payment
        payment = Payment.objects.create(
            user=self.user,
            idempotency_key='audit-test',
            amount=Decimal('250.00'),
            status='COMPLETED'
        )
        
        # Create audit logs
        AuditLog.objects.create(
            payment=payment,
            action='PAYMENT_CREATED',
            details={'amount': 250.00},
            user=self.user
        )
        AuditLog.objects.create(
            payment=payment,
            action='PAYMENT_VERIFIED',
            details={'verified_by': 'system'},
            user=None
        )
        
        # Get audit trail
        audit_url = f'/api/payments/{payment.id}/audit-trail/'
        response = self.client.get(audit_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['action'], 'PAYMENT_VERIFIED')  # Newest first