from django.shortcuts import render

from accounts.decorators import role_required
from .models import AuditLog


@role_required('DISTRIBUTOR')
def index(request):
    # AuditLog.user can be null (on_delete=SET_NULL), so entries left behind
    # by a deleted user aren't attributable to any distributor and are
    # excluded here rather than shown to everyone.
    logs = AuditLog.objects.filter(
        user__distributor=request.user.distributor
    ).order_by('-timestamp')
    return render(request, 'audit/index.html', {'logs': logs})
