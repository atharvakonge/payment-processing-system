from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, WebhookViewSet, index

# Create router
router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'webhooks', WebhookViewSet, basename='webhook')

urlpatterns = [
    path('', index, name='index'),
    path('api/', include(router.urls)),
]