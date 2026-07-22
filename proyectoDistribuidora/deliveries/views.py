from django.contrib import messages
from django.db import IntegrityError, transaction
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render, redirect

from accounts.decorators import role_required
from accounts.models import Notification
from audit.models import AuditLog
from orders.models import Order, OrderStatus
from .models import DeliveryConfirmation
from .forms import DeliveryConfirmationForm


@role_required('DELIVERY', 'DISTRIBUTOR')
def index(request):
    pending = (
        Order.objects
        .filter(store__distributor=request.user.distributor, status=OrderStatus.DISPATCHED)
        .select_related('store', 'vendor')
        .prefetch_related('items__product')
        .order_by('created_at')
    )
    history = (
        DeliveryConfirmation.objects
        .filter(order__store__distributor=request.user.distributor)
        .select_related('order__store', 'order__vendor', 'delivery_user')
        .order_by('-confirmed_at')[:20]
    )
    issues_qs = (
        Order.objects
        .filter(store__distributor=request.user.distributor, status=OrderStatus.DELIVERY_ISSUE)
        .select_related('store', 'vendor')
        .order_by('updated_at')
    )
    if request.user.role == 'DELIVERY':
        issues_qs = issues_qs.filter(delivery_confirmation__delivery_user=request.user)
    return render(request, 'deliveries/index.html', {
        'pending': pending,
        'issues': issues_qs,
        'history': history,
    })


@role_required('DELIVERY')
def crear_confirmacion(request):
    return redirect('index_deliveries')


@role_required('DELIVERY')
def ver_pedido_entrega(request, order_id):
    order = get_object_or_404(
        Order.objects
        .filter(store__distributor=request.user.distributor)
        .select_related('store', 'vendor')
        .prefetch_related('items__product'),
        pk=order_id,
    )
    order_total = sum(i.unit_price_at_time * i.quantity for i in order.items.all())
    return render(request, 'deliveries/ver_pedido_entrega.html', {
        'order': order,
        'order_total': order_total,
        'is_dispatched': order.status == OrderStatus.DISPATCHED,
    })


@role_required('DELIVERY')
def confirmar_entrega(request, order_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update().filter(
                store__distributor=request.user.distributor,
                status=OrderStatus.DISPATCHED,  # this IS the status guard — do not remove
            ),
            pk=order_id,
        )
        try:
            DeliveryConfirmation.objects.create(order=order, delivery_user=request.user)
        except IntegrityError:
            messages.error(request, 'Este pedido ya fue confirmado por otro repartidor.')
            return redirect('index_deliveries')
        order.status = OrderStatus.DELIVERED
        order.save(update_fields=['status', 'updated_at'])
        AuditLog.objects.create(
            user=request.user,
            action='order_delivered',
            entity_type='Order',
            entity_id=str(order.id),
            previous_status=OrderStatus.DISPATCHED,
            new_status=OrderStatus.DELIVERED,
        )
        Notification.objects.create(  # Store.owner is a non-nullable FK
            user=order.store.owner,
            order=order,
            message=f'Tu pedido #{order.id} fue entregado. Confírmalo cuando lo recibas.',
        )
    messages.success(request, 'Entrega confirmada.')
    return redirect('index_deliveries')


@role_required('DELIVERY', 'DISTRIBUTOR')
def editar_confirmacion(request, id):
    lookup = {'id': id, 'order__store__distributor': request.user.distributor}
    if request.user.role == 'DELIVERY':
        lookup['delivery_user'] = request.user
    confirmacion = get_object_or_404(DeliveryConfirmation, **lookup)
    if request.method == 'POST':
        formulario = DeliveryConfirmationForm(
            request.POST, instance=confirmacion, distributor=request.user.distributor
        )
        if formulario.is_valid():
            formulario.save()
            return redirect('index_deliveries')
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
    return redirect('index_deliveries')
