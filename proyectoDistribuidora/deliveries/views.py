from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect

from accounts.decorators import role_required
from accounts.models import Notification
from audit.models import AuditLog
from orders.models import OrderStatus
from .models import DeliveryConfirmation
from .forms import DeliveryConfirmationForm


@role_required('DELIVERY', 'DISTRIBUTOR')
def index(request):
    # NFR-02.5: deliveries/index.html displays order and delivery_user per
    # row — eager-load to avoid an N+1 per confirmation.
    confirmaciones = DeliveryConfirmation.objects.filter(
        order__store__distributor=request.user.distributor
    ).select_related('order', 'delivery_user')
    return render(request, 'deliveries/index.html', {'confirmaciones': confirmaciones})


@role_required('DELIVERY')
def crear_confirmacion(request):
    if request.method == 'POST':
        formulario = DeliveryConfirmationForm(request.POST, distributor=request.user.distributor)
        if formulario.is_valid():
            with transaction.atomic():
                confirmacion = formulario.save(commit=False)
                confirmacion.delivery_user = request.user
                confirmacion.save()

                pedido = confirmacion.order
                previous_status = pedido.status
                pedido.status = OrderStatus.DELIVERED
                pedido.save(update_fields=['status', 'updated_at'])

                AuditLog.objects.create(
                    user=request.user,
                    action='order_delivered',
                    entity_type='Order',
                    entity_id=str(pedido.id),
                    previous_status=previous_status,
                    new_status=OrderStatus.DELIVERED,
                )

                Notification.objects.create(
                    user=pedido.store.owner,
                    order=pedido,
                    message=f'Tu pedido #{pedido.id} fue entregado. Confírmalo cuando lo recibas.',
                )
            return redirect(index)
    else:
        formulario = DeliveryConfirmationForm(distributor=request.user.distributor)
    return render(request, 'deliveries/crear_confirmacion.html', {'formulario': formulario})


@role_required('DELIVERY', 'DISTRIBUTOR')
def editar_confirmacion(request, id):
    lookup = {'id': id, 'order__store__distributor': request.user.distributor}
    if request.user.role == 'DELIVERY':
        # A delivery person may only amend confirmations they made themselves.
        lookup['delivery_user'] = request.user
    confirmacion = get_object_or_404(DeliveryConfirmation, **lookup)
    if request.method == 'POST':
        formulario = DeliveryConfirmationForm(
            request.POST, instance=confirmacion, distributor=request.user.distributor
        )
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = DeliveryConfirmationForm(instance=confirmacion, distributor=request.user.distributor)
    return render(request, 'deliveries/editar_confirmacion.html', {
        'formulario': formulario,
        'confirmacion': confirmacion,
    })


@role_required('DISTRIBUTOR')
def eliminar_confirmacion(request, id):
    get_object_or_404(
        DeliveryConfirmation, id=id, order__store__distributor=request.user.distributor
    ).delete()
    return redirect(index)
