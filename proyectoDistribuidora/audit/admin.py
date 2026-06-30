from django.contrib import admin
from .models import AuditLog

class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'entity_type', 'entity_id', 'user', 'timestamp')
    list_filter = ('action', 'entity_type')

admin.site.register(AuditLog, AuditLogAdmin)
