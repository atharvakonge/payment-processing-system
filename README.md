# Payment Processing System

A production-grade payment processing API built with **Django REST Framework** and **PostgreSQL**, featuring idempotent request handling, automated refund workflows, and comprehensive audit logging for financial compliance.

![Django](https://img.shields.io/badge/Django-6.0-092E20?logo=django)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)
![DRF](https://img.shields.io/badge/DRF-3.15-red)

## ✨ Features

- **Idempotent Payments**: Prevents duplicate charges using idempotency keys
- **Automated Refund Workflows**: Full and partial refund support with validation
- **Audit Logging**: Immutable audit trail with cryptographic signatures for compliance
- **RESTful API**: Clean API design with Django REST Framework
- **ACID Transactions**: Database transactions ensure data consistency
- **Comprehensive Testing**: 10 unit tests with 88% code coverage
- **Webhook Integration**: Simulated payment provider webhooks
- **Admin Interface**: Django admin for payment management

## 🏗️ Architecture

### System Design
```
Client Request → Django REST Framework → Serializer Validation
                                              ↓
                                    Idempotency Check
                                              ↓
                                    Database Transaction (@atomic)
                                              ↓
                            Payment Created + Audit Log
                                              ↓
                                    JSON Response
```

### Database Schema
```sql
payments_payment
├── id (UUID PRIMARY KEY)
├── idempotency_key (VARCHAR UNIQUE)  -- Prevents duplicates
├── user_id (FK → auth_user)
├── amount (DECIMAL)
├── currency (VARCHAR)
├── status (VARCHAR: PENDING/COMPLETED/REFUNDED)
└── created_at (TIMESTAMP)

payments_refund
├── id (UUID PRIMARY KEY)
├── payment_id (FK → payments_payment)
├── amount (DECIMAL)
├── reason (TEXT)
└── status (VARCHAR)

payments_auditlog
├── id (SERIAL PRIMARY KEY)
├── payment_id (FK → payments_payment)
├── action (VARCHAR)
├── details (JSONB)              -- Flexible compliance data
├── user_id (FK → auth_user)
└── timestamp (TIMESTAMP)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### Installation
```bash
# Clone repository
git clone https://github.com/yourusername/payment-processing-api.git
cd payment-processing-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL
docker-compose up -d

# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

Open your browser: **http://127.0.0.1:8000**

## 📡 API Endpoints

### Payment Operations
```http
POST   /api/payments/                    # Create payment (idempotent)
GET    /api/payments/                    # List all payments
GET    /api/payments/{id}/               # Get payment details
POST   /api/payments/{id}/refund/        # Refund payment
GET    /api/payments/{id}/audit-trail/   # Get audit logs
GET    /api/payments/my-payments/        # Current user's payments
```

### Example: Create Payment
```bash
curl -X POST http://127.0.0.1:8000/api/payments/ \
  -H "Content-Type: application/json" \
  -d '{
    "idempotency_key": "payment-001",
    "amount": "150.50",
    "currency": "USD",
    "description": "Product purchase"
  }'
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "idempotency_key": "payment-001",
  "user": 1,
  "amount": "150.50",
  "currency": "USD",
  "status": "COMPLETED",
  "description": "Product purchase",
  "created_at": "2026-01-27T21:15:30Z",
  "updated_at": "2026-01-27T21:15:30Z"
}
```

### Example: Refund Payment
```bash
curl -X POST http://127.0.0.1:8000/api/payments/{id}/refund/ \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "50.00",
    "reason": "Customer request"
  }'
```

### Example: Idempotency Test
```bash
# Send same request twice
curl -X POST http://127.0.0.1:8000/api/payments/ \
  -H "Content-Type: application/json" \
  -d '{"idempotency_key": "test-123", "amount": "100.00"}'

# Second request returns SAME payment (no duplicate charge!)
```

## 🧪 Testing

### Run Tests
```bash
# All tests
python manage.py test payments

# Verbose output
python manage.py test payments --verbosity=2

# With coverage
coverage run --source='.' manage.py test payments
coverage report
coverage html  # Generate HTML report
```

### Test Results
```
✅ 10/10 tests passing
✅ 88% code coverage
✅ Tests include:
   - Payment creation with idempotency
   - Duplicate prevention
   - Refund workflows
   - Validation and error handling
   - Audit logging verification
   - Edge cases (negative amounts, already refunded, etc.)
```

## 🔧 Technical Decisions

### Idempotency Implementation

**Problem:** Network failures cause duplicate payment requests

**Solution:** Idempotency keys
```python
# Check if payment with same key exists
existing = Payment.objects.filter(idempotency_key=key).first()
if existing:
    return existing  # Return existing, don't create duplicate

# Otherwise create new payment
payment = Payment.objects.create(...)
```

**Critical for financial APIs** - prevents double-charging customers during network retries.

---

### Database Transactions

**All multi-step operations wrapped in transactions:**
```python
@transaction.atomic
def create(self, request):
    payment = Payment.objects.create(...)
    AuditLog.objects.create(...)
    # Both succeed or both rollback
```

**Ensures data consistency** - can't have payment without audit log, or refund without status update.

---

### Audit Logging Strategy

**Immutable append-only log for compliance:**
- Every payment state change creates audit record
- JSONField stores flexible metadata
- Cryptographic signatures (SHA-256) for verification
- Cannot be modified (read-only in admin)

**Regulatory compliance** - proves payment history for audits, disputes, chargebacks.

---

### UUID Primary Keys

**Why UUID over auto-increment:**
- ✅ Non-sequential (can't enumerate all payments)
- ✅ Globally unique (can merge databases)
- ✅ Generated client-side (distributed systems)
- ✅ Security (harder to guess payment IDs)

---

## 🛠️ Technology Stack

- **Backend**: Django 6.0, Django REST Framework 3.15
- **Database**: PostgreSQL 15 with JSONB support
- **API**: RESTful with automatic OpenAPI documentation
- **Testing**: Django TestCase, APIClient
- **Containerization**: Docker Compose

## 📊 Performance Characteristics

- **Idempotency**: O(1) lookup with unique index
- **Refund processing**: ACID-compliant with rollback support
- **Audit queries**: Indexed on payment_id and timestamp
- **Pagination**: 20 records per page (configurable)

## 🎯 Key Learnings

This project demonstrates:

1. **Django ORM**: Models, migrations, complex queries
2. **Django REST Framework**: Serializers, ViewSets, custom actions
3. **Financial Systems**: Idempotency, audit trails, refund workflows
4. **Database Transactions**: ACID compliance with @transaction.atomic
5. **API Design**: RESTful endpoints with proper error handling
6. **Testing**: Comprehensive test coverage with edge cases

## 🔐 Security Features

- **Idempotency keys**: Prevent duplicate transactions
- **Database constraints**: Enforce data integrity (CHECK, UNIQUE)
- **Transaction isolation**: Prevent race conditions
- **Audit logging**: Tamper-evident compliance trail
- **Input validation**: Serializer-level validation for all inputs

## 🚧 Future Enhancements

- [ ] JWT authentication and user management
- [ ] Rate limiting with Redis (prevent API abuse)
- [ ] Celery for async webhook processing
- [ ] Stripe/PayPal integration (real payment providers)
- [ ] Multi-currency support with exchange rates
- [ ] Dispute management workflows
- [ ] Chargeback handling
- [ ] Payment analytics dashboard

## 📚 API Documentation

### Create Payment

**Endpoint:** `POST /api/payments/`

**Request:**
```json
{
  "idempotency_key": "unique-key-123",
  "amount": "100.50",
  "currency": "USD",
  "description": "Order #12345"
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "idempotency_key": "unique-key-123",
  "amount": "100.50",
  "status": "COMPLETED",
  "created_at": "2026-01-27T21:15:30Z"
}
```

**Idempotent Behavior:**
- Same request with same idempotency_key → Returns existing payment (200 OK)
- Different idempotency_key → Creates new payment (201 Created)

---

### Refund Payment

**Endpoint:** `POST /api/payments/{id}/refund/`

**Request:**
```json
{
  "amount": "50.00",
  "reason": "Customer requested refund"
}
```

**Response (201 Created):**
```json
{
  "id": "abc-123...",
  "payment_id": "550e8400...",
  "amount": "50.00",
  "reason": "Customer requested refund",
  "status": "COMPLETED",
  "created_at": "2026-01-27T21:20:15Z"
}
```

**Business Rules:**
- ❌ Cannot refund already-refunded payment
- ❌ Refund amount cannot exceed payment amount
- ✅ Payment status updates to "REFUNDED"
- ✅ Audit log created automatically

---

### Get Audit Trail

**Endpoint:** `GET /api/payments/{id}/audit-trail/`

**Response:**
```json
[
  {
    "action": "PAYMENT_CREATED",
    "details": {"amount": 150.50, "currency": "USD"},
    "timestamp": "2026-01-27T21:15:30Z"
  },
  {
    "action": "PAYMENT_REFUNDED",
    "details": {"refund_id": "abc-123", "amount": 50.00},
    "timestamp": "2026-01-27T21:20:15Z"
  }
]
```

## 🖥️ Admin Interface

Django provides auto-generated admin interface:

**Access:** http://127.0.0.1:8000/admin/

**Features:**
- Payment management with filtering and search
- Refund tracking
- Audit log viewer (read-only)
- Bulk operations
- Export capabilities

## 📄 License

MIT

## 👤 Author

**Atharva Konge**
- GitHub: [@atharvakonge](https://github.com/atharvakonge)

---