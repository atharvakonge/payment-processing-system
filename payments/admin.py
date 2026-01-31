from django.contrib import admin
from .models import Payment, Refund, AuditLog

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['idempotency_key', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('user', 'amount', 'currency', 'status', 'description')
        }),
        ('Idempotency', {
            'fields': ('idempotency_key',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['id', 'payment', 'amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    readonly_fields = ['id', 'created_at']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'payment', 'user', 'timestamp']
    list_filter = ['action', 'timestamp']
    readonly_fields = ['payment', 'action', 'details', 'user', 'timestamp']
    
    # Make it read-only (audit logs shouldn't be edited!)
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False