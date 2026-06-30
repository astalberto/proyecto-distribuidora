from django.shortcuts import render
from .models import AuditLog


def index(request):
    logs = AuditLog.objects.all().order_by('-timestamp')
    return render(request, 'audit/index.html', {'logs': logs})
