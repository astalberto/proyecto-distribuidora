from django.db import models

from accounts.models import User


class AuditLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs"
    )

    action = models.CharField(max_length=100)

    entity_type = models.CharField(max_length=100)

    entity_id = models.CharField(max_length=100)

    timestamp = models.DateTimeField(auto_now_add=True)

    details = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.action} - {self.entity_type}"