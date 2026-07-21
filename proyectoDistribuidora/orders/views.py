from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import Notification
from audit.models import AuditLog
from catalog.models import VendorInventory
from .models import Order, OrderItem, OrderStatus
from .forms import OrderForm, OrderItemForm, ReportarIncidenciaForm, ResolverIncidenciaForm


def _orders_for(user):
    """Scope the Order queryset to what this role is allowed to see."""
    if user.role == 'STORE_OWNER':
        qs = Order.objects.filter(store__owner=user)
    elif user.role == 'VENDOR':
        qs = Order.objects.filter(vendor=user)
    elif user.role == 'DISTRIBUTOR':
        qs = Order.objects.filter(store__distributor=user.distributor)
    else:
        return Order.objects.none()
    # NFR-02.5: index.html/ver_pedido.html both display store and vendor
    # per row — eager-load to avoid an N+1 per order.
    return qs.select_related('store', 'vendor')


@role_required('STORE_OWNER', 'VENDOR', 'DISTRIBUTOR')
def index(request):
    return render(request, 'orders/index.html', {'pedidos': _orders_for(request.user)})


@role_required('STORE_OWNER')
def crear_pedido(request):
    if request.method == 'POST':
        formulario = OrderForm(request.POST, owner=request.user)
        if formulario.is_valid():
            pedido = formulario.save(commit=False)
            # DR-01: vendor derived from store.vendor, not supplied by the form
            if not pedido.store.vendor:
                formulario.add_error(
                    'store',
                    'Esta tienda no tiene un vendedor asignado. Contacta al distribuidor.'
                )
            else:
                pedido.vendor = pedido.store.vendor
                pedido.save()
                return redirect('ver_pedido', id=pedido.id)
    else:
        formulario = OrderForm(owner=request.user)
    return render(request, 'orders/crear_pedido.html', {'formulario': formulario})


@role_required('STORE_OWNER', 'VENDOR', 'DISTRIBUTOR')
def ver_pedido(request, id):
    pedido = get_object_or_404(_orders_for(request.user), id=id)
    return render(request, 'orders/ver_pedido.html', {
        'pedido': pedido,
        'items': pedido.items.select_related('product').all(),
    })


@role_required('STORE_OWNER')
def cancelar_pedido(request, id):
    """US-23: a store owner may withdraw an order only while it's still
    PENDING — once a vendor has acted on it, only they can reject it."""
    pedido = get_object_or_404(
        Order, id=id, store__owner=request.user, status=OrderStatus.PENDING
    )
    if request.method == 'POST':
        pedido.status = OrderStatus.REJECTED
        pedido.rejection_reason = 'Cancelado por el propietario de la tienda'
        pedido.save(update_fields=['status', 'rejection_reason', 'updated_at'])
        AuditLog.objects.create(
            user=request.user,
            action='order_cancelled',
            entity_type='Order',
            entity_id=str(pedido.id),
            previous_status=OrderStatus.PENDING,
            new_status=OrderStatus.REJECTED,
            details={'rejection_reason': pedido.rejection_reason},
        )
        messages.success(request, 'Pedido cancelado.')
    return redirect('ver_pedido', id=id)


@role_required('STORE_OWNER')
def crear_item_pedido(request, order_id):
    pedido = get_object_or_404(
        Order, id=order_id, store__owner=request.user, status=OrderStatus.PENDING
    )
    if request.method == 'POST':
        formulario = OrderItemForm(request.POST, vendor=pedido.vendor)
        if formulario.is_valid():
            item = formulario.save(commit=False)
            item.order = pedido
            item.unit_price_at_time = item.product.unit_price
            item.save()
            return redirect('ver_pedido', id=order_id)
    else:
        formulario = OrderItemForm(vendor=pedido.vendor)
    return render(request, 'orders/crear_item_pedido.html', {
        'formulario': formulario,
        'pedido': pedido,
    })


@role_required('STORE_OWNER')
def editar_item_pedido(request, id):
    item = get_object_or_404(
        OrderItem, id=id, order__store__owner=request.user, order__status=OrderStatus.PENDING
    )
    if request.method == 'POST':
        formulario = OrderItemForm(request.POST, instance=item, vendor=item.order.vendor)
        if formulario.is_valid():
            item = formulario.save(commit=False)
            item.unit_price_at_time = item.product.unit_price
            item.save()
            return redirect('ver_pedido', id=item.order.id)
    else:
        formulario = OrderItemForm(instance=item, vendor=item.order.vendor)
    return render(request, 'orders/editar_item_pedido.html', {
        'formulario': formulario,
        'item': item,
    })


@role_required('STORE_OWNER')
def eliminar_item_pedido(request, id):
    item = get_object_or_404(
        OrderItem, id=id, order__store__owner=request.user, order__status=OrderStatus.PENDING
    )
    order_id = item.order.id
    item.delete()
    return redirect('ver_pedido', id=order_id)


# --- Vendor state-machine transitions (UC-11, UC-12, UC-13) ---

@role_required('VENDOR')
def aceptar_pedido(request, id):
    pedido = get_object_or_404(Order, id=id, vendor=request.user, status=OrderStatus.PENDING)
    if request.method == 'POST':
        items = list(pedido.items.select_related('product'))
        if not items:
            messages.error(request, 'El pedido no tiene items.')
            return redirect('ver_pedido', id=id)

        with transaction.atomic():
            # Lock the vendor's inventory rows for every ordered product so
            # a concurrent accept on another order can't double-spend the
            # same stock (NFR-03.1, NFR-03.3, UC-11 step 3-4).
            inventarios = {
                inv.product_id: inv
                for inv in VendorInventory.objects.select_for_update().filter(
                    vendor=request.user,
                    product_id__in=[item.product_id for item in items],
                )
            }
            errores = []
            for item in items:
                inv = inventarios.get(item.product_id)
                disponible = inv.quantity if inv else 0
                if disponible < item.quantity:
                    errores.append(
                        f'{item.product.name}: disponible {disponible}, solicitado {item.quantity}'
                    )
            if errores:
                # Nothing has been written yet — the transaction commits
                # empty, so the order stays PENDING (NFR-03.2, UC-11 Alt A1).
                for error in errores:
                    messages.error(request, error)
                AuditLog.objects.create(
                    user=request.user,
                    action='order_accept_failed',
                    entity_type='Order',
                    entity_id=str(pedido.id),
                    details={'errors': errores},
                )
                return redirect('ver_pedido', id=id)

            deducciones = []
            for item in items:
                inv = inventarios[item.product_id]
                inv.quantity -= item.quantity
                inv.save(update_fields=['quantity'])
                deducciones.append({
                    'product': item.product.name,
                    'quantity_deducted': item.quantity,
                    'remaining_stock': inv.quantity,
                })

            pedido.status = OrderStatus.ACCEPTED
            pedido.save(update_fields=['status', 'updated_at'])
            AuditLog.objects.create(
                user=request.user,
                action='order_accepted',
                entity_type='Order',
                entity_id=str(pedido.id),
                previous_status=OrderStatus.PENDING,
                new_status=OrderStatus.ACCEPTED,
                details={'inventory_deductions': deducciones},
            )
            Notification.objects.create(
                user=pedido.store.owner,
                order=pedido,
                message=f'Tu pedido #{pedido.id} fue aceptado.',
            )

        messages.success(request, 'Pedido aceptado — inventario actualizado.')
    return redirect('ver_pedido', id=id)


@role_required('VENDOR')
def rechazar_pedido(request, id):
    pedido = get_object_or_404(Order, id=id, vendor=request.user, status=OrderStatus.PENDING)
    if request.method == 'POST':
        pedido.status = OrderStatus.REJECTED
        pedido.rejection_reason = request.POST.get('rejection_reason', '').strip()[:500]
        pedido.save(update_fields=['status', 'rejection_reason', 'updated_at'])
        AuditLog.objects.create(
            user=request.user,
            action='order_rejected',
            entity_type='Order',
            entity_id=str(pedido.id),
            previous_status=OrderStatus.PENDING,
            new_status=OrderStatus.REJECTED,
            details={'rejection_reason': pedido.rejection_reason},
        )
        Notification.objects.create(
            user=pedido.store.owner,
            order=pedido,
            message=(
                f'Tu pedido #{pedido.id} fue rechazado.'
                + (f' Motivo: {pedido.rejection_reason}' if pedido.rejection_reason else '')
            ),
        )
        messages.success(request, 'Pedido rechazado.')
        return redirect('ver_pedido', id=id)
    return render(request, 'orders/rechazar_pedido.html', {'pedido': pedido})


@role_required('VENDOR')
def despachar_pedido(request, id):
    pedido = get_object_or_404(Order, id=id, vendor=request.user, status=OrderStatus.ACCEPTED)
    if request.method == 'POST':
        pedido.status = OrderStatus.DISPATCHED
        pedido.save(update_fields=['status', 'updated_at'])
        AuditLog.objects.create(
            user=request.user,
            action='order_dispatched',
            entity_type='Order',
            entity_id=str(pedido.id),
            previous_status=OrderStatus.ACCEPTED,
            new_status=OrderStatus.DISPATCHED,
        )
        Notification.objects.create(
            user=pedido.store.owner,
            order=pedido,
            message=f'Tu pedido #{pedido.id} fue despachado.',
        )
        messages.success(request, 'Pedido marcado como despachado.')
    return redirect('ver_pedido', id=id)


# --- Post-delivery confirmation / dispute (DR-09) ---

@role_required('STORE_OWNER')
def confirmar_recepcion(request, id):
    pedido = get_object_or_404(
        Order, id=id, store__owner=request.user, status=OrderStatus.DELIVERED
    )
    if request.method == 'POST':
        pedido.status = OrderStatus.CONFIRMED
        pedido.save(update_fields=['status', 'updated_at'])
        AuditLog.objects.create(
            user=request.user,
            action='order_confirmed',
            entity_type='Order',
            entity_id=str(pedido.id),
            previous_status=OrderStatus.DELIVERED,
            new_status=OrderStatus.CONFIRMED,
        )
        Notification.objects.create(
            user=pedido.vendor,
            order=pedido,
            message=f'La tienda {pedido.store.name} confirmó la recepción del pedido #{pedido.id}.',
        )
        messages.success(request, 'Recepción confirmada.')
    return redirect('ver_pedido', id=id)


@role_required('STORE_OWNER')
def reportar_incidencia(request, id):
    pedido = get_object_or_404(
        Order, id=id, store__owner=request.user, status=OrderStatus.DELIVERED
    )
    if request.method == 'POST':
        formulario = ReportarIncidenciaForm(request.POST, instance=pedido)
        if formulario.is_valid():
            incidencia = formulario.save(commit=False)
            incidencia.status = OrderStatus.DELIVERY_ISSUE
            incidencia.issue_reported_at = timezone.now()
            incidencia.save(update_fields=[
                'status', 'issue_description', 'issue_reported_at', 'updated_at'
            ])
            Notification.objects.create(
                user=pedido.vendor,
                order=pedido,
                message=f'La tienda {pedido.store.name} reportó un problema con el pedido #{pedido.id}.',
            )
            # The delivery person who dropped it off, if we have one on record.
            confirmacion = getattr(pedido, 'delivery_confirmation', None)
            if confirmacion is not None:
                Notification.objects.create(
                    user=confirmacion.delivery_user,
                    order=pedido,
                    message=f'Se reportó un problema con la entrega del pedido #{pedido.id}.',
                )
            messages.success(request, 'Incidencia reportada.')
            return redirect('ver_pedido', id=id)
    else:
        formulario = ReportarIncidenciaForm(instance=pedido)
    return render(request, 'orders/reportar_incidencia.html', {
        'formulario': formulario,
        'pedido': pedido,
    })


@role_required('VENDOR')
def resolver_incidencia(request, id):
    pedido = get_object_or_404(
        Order, id=id, vendor=request.user, status=OrderStatus.DELIVERY_ISSUE
    )
    if request.method == 'POST':
        formulario = ResolverIncidenciaForm(request.POST, instance=pedido)
        if formulario.is_valid():
            resuelto = formulario.save(commit=False)
            resuelto.status = OrderStatus.CONFIRMED
            resuelto.resolved_at = timezone.now()
            resuelto.save(update_fields=[
                'status', 'resolution_notes', 'resolved_at', 'updated_at'
            ])
            AuditLog.objects.create(
                user=request.user,
                action='delivery_issue_resolved',
                entity_type='Order',
                entity_id=str(pedido.id),
                previous_status=OrderStatus.DELIVERY_ISSUE,
                new_status=OrderStatus.CONFIRMED,
                details={'resolution_notes': resuelto.resolution_notes},
            )
            Notification.objects.create(
                user=pedido.store.owner,
                order=pedido,
                message=f'El vendedor resolvió la incidencia del pedido #{pedido.id}.',
            )
            messages.success(request, 'Incidencia resuelta.')
            return redirect('ver_pedido', id=id)
    else:
        formulario = ResolverIncidenciaForm(instance=pedido)
    return render(request, 'orders/resolver_incidencia.html', {
        'formulario': formulario,
        'pedido': pedido,
    })


# --- JSON polling endpoint — vendor dashboard, 30s interval (FR-06.6, FR-10.1) ---

@role_required('VENDOR')
def pending_orders_api(request):
    pedidos = (
        Order.objects.filter(vendor=request.user, status=OrderStatus.PENDING)
        .select_related('store')
        .annotate(item_count=Count('items'))  # avoids one COUNT query per order
        .order_by('created_at')
    )
    return JsonResponse({
        'orders': [
            {
                'id': p.id,
                'store': p.store.name,
                'created_at': p.created_at.isoformat(),
                'item_count': p.item_count,
                'url': f'/orders/{p.id}/',
            }
            for p in pedidos
        ],
    })
