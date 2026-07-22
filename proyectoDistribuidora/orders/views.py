from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import Notification
from audit.models import AuditLog
from catalog.models import Category, Product, ProductImage, ProductStatus, StockLevel, Store, Warehouse
from .models import Order, OrderItem, OrderStatus
from .forms import OrderForm, OrderItemForm, ReportarIncidenciaForm, ResolverIncidenciaForm


def _ensure_cart(request, product_id, quantity):
    cart = request.session.get('cart')
    if cart:
        return cart, None

    stores = list(Store.objects.filter(owner=request.user, vendor__isnull=False))
    if not stores:
        messages.error(request, 'No tienes tiendas con vendedor asignado. Contacta al distribuidor.')
        return None, redirect('explorar_productos')
    if len(stores) == 1:
        cart = {'store_id': stores[0].id, 'items': []}
        request.session['cart'] = cart
        return cart, None

    store_id = request.POST.get('store_id')
    if not store_id:
        return None, render(request, 'orders/seleccionar_tienda.html', {
            'stores': stores,
            'product_id': product_id,
            'quantity': quantity,
        })
    try:
        store = next(s for s in stores if str(s.id) == store_id)
    except StopIteration:
        messages.error(request, 'Tienda no válida.')
        return None, redirect('explorar_productos')
    cart = {'store_id': store.id, 'items': []}
    request.session['cart'] = cart
    return cart, None


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
def iniciar_carrito(request):
    if request.method == 'POST':
        formulario = OrderForm(request.POST, owner=request.user)
        if formulario.is_valid():
            store = formulario.cleaned_data['store']
            if not store.vendor:
                formulario.add_error(
                    'store',
                    'Esta tienda no tiene un vendedor asignado. Contacta al distribuidor.'
                )
            else:
                request.session['cart'] = {'store_id': store.id, 'items': []}
                return redirect('carrito')
    else:
        formulario = OrderForm(owner=request.user)
    return render(request, 'orders/iniciar_carrito.html', {'formulario': formulario})


@role_required('STORE_OWNER')
def carrito(request):
    cart = request.session.get('cart')
    if not cart:
        return redirect('explorar_productos')
    store = get_object_or_404(
        Store.objects.select_related('vendor', 'distributor'),
        pk=cart['store_id'], owner=request.user,
    )

    if request.method == 'POST':
        if 'add' in request.POST:
            formulario = OrderItemForm(request.POST, vendor=store.vendor)
            if formulario.is_valid():
                product = formulario.cleaned_data['product']
                quantity = formulario.cleaned_data['quantity']
                items = cart['items']
                for item in items:
                    if item['product_id'] == product.id:
                        item['quantity'] = quantity
                        break
                else:
                    items.append({'product_id': product.id, 'quantity': quantity})
                request.session.modified = True
                return redirect('carrito')
            # fall through to re-render with form errors
        else:
            # Single cart form: always apply qty edits first, then branch on button.
            for item in cart['items']:
                key = f"qty_{item['product_id']}"
                if key in request.POST:
                    try:
                        item['quantity'] = max(1, int(request.POST[key]))
                    except (ValueError, TypeError):
                        pass
            request.session.modified = True

            if 'confirm' in request.POST:
                return redirect('confirmar_carrito')
            elif 'discard' in request.POST:
                del request.session['cart']
                return redirect('index_orders')
            elif 'remove' in request.POST:
                try:
                    product_id = int(request.POST['remove'])
                except (ValueError, TypeError):
                    product_id = 0
                cart['items'] = [i for i in cart['items'] if i['product_id'] != product_id]
                request.session.modified = True
                return redirect('carrito')

    product_ids = [i['product_id'] for i in cart['items']]
    products = {p.id: p for p in Product.objects.filter(id__in=product_ids)}
    display_items = []
    for i in cart['items']:
        if i['product_id'] not in products:
            continue
        product = products[i['product_id']]
        qty = i['quantity']
        price = product.current_price()
        display_items.append({'product': product, 'quantity': qty, 'subtotal': price * qty})
    cart_total = sum(item['subtotal'] for item in display_items)
    return render(request, 'orders/carrito.html', {
        'store': store,
        'display_items': display_items,
        'cart_total': cart_total,
    })


@role_required('STORE_OWNER')
def confirmar_carrito(request):
    cart = request.session.get('cart')
    if not cart or not cart['items']:
        return redirect('carrito')
    store = get_object_or_404(
        Store.objects.select_related('vendor', 'distributor'),
        pk=cart['store_id'], owner=request.user,
    )

    if request.method == 'POST':
        with transaction.atomic():
            pedido = Order.objects.create(
                store=store,
                vendor=store.vendor,
                status=OrderStatus.PENDING,
            )
            default_warehouse = Warehouse.get_or_create_default(store.distributor)
            for item_data in cart['items']:
                try:
                    product = Product.objects.get(
                        id=item_data['product_id'],
                        distributor=store.distributor,
                        status=ProductStatus.ACTIVE,
                    )
                except Product.DoesNotExist:
                    continue
                OrderItem.objects.create(
                    order=pedido,
                    product=product,
                    quantity=item_data['quantity'],
                    unit_price_at_time=product.current_price(),
                    warehouse=default_warehouse,
                )
            AuditLog.objects.create(
                user=request.user,
                action='order_created',
                entity_type='Order',
                entity_id=str(pedido.id),
                new_status=OrderStatus.PENDING,
            )
        del request.session['cart']
        return redirect('ver_pedido', id=pedido.id)

    product_ids = [i['product_id'] for i in cart['items']]
    products = {p.id: p for p in Product.objects.filter(id__in=product_ids)}
    display_items = []
    for i in cart['items']:
        if i['product_id'] not in products:
            continue
        product = products[i['product_id']]
        qty = i['quantity']
        price = product.current_price()
        display_items.append({'product': product, 'quantity': qty, 'subtotal': price * qty})
    cart_total = sum(item['subtotal'] for item in display_items)
    return render(request, 'orders/confirmar_carrito.html', {
        'store': store,
        'display_items': display_items,
        'cart_total': cart_total,
    })


@role_required('STORE_OWNER')
def explorar_productos(request):
    distributor = request.user.distributor

    if request.method == 'POST':
        try:
            product_id = int(request.POST.get('product_id', 0))
            quantity = max(1, int(request.POST.get('quantity', 1)))
        except (ValueError, TypeError):
            return redirect('explorar_productos')

        cart, response = _ensure_cart(request, product_id, quantity)
        if response is not None:
            return response

        try:
            product = Product.objects.get(
                id=product_id, distributor=distributor, status=ProductStatus.ACTIVE,
            )
        except Product.DoesNotExist:
            return redirect('explorar_productos')

        items = cart['items']
        for item in items:
            if item['product_id'] == product.id:
                item['quantity'] = quantity
                break
        else:
            items.append({'product_id': product.id, 'quantity': quantity})
        request.session.modified = True
        return redirect('explorar_productos')

    # GET
    products_qs = (
        Product.objects.filter(distributor=distributor, status=ProductStatus.ACTIVE)
        .select_related('category', 'brand')
        .prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_main=True), to_attr='main_images')
        )
        .order_by('name')
    )
    q = request.GET.get('q', '').strip()
    if q:
        products_qs = products_qs.filter(name__icontains=q)
    categoria_id = request.GET.get('categoria', '').strip()
    if categoria_id:
        products_qs = products_qs.filter(category_id=categoria_id)

    categorias = Category.objects.filter(distributor=distributor).order_by('name')
    cart = request.session.get('cart')
    cart_map = {item['product_id']: item['quantity'] for item in cart['items']} if cart else {}
    store = Store.objects.filter(pk=cart['store_id'], owner=request.user).first() if cart else None

    display_products = []
    for product in products_qs:
        display_products.append({
            'product': product,
            'price': product.current_price(),
            'stock': product.total_stock(),
            'in_cart': cart_map.get(product.id, 0),
            'main_image': product.main_images[0] if product.main_images else None,
        })

    return render(request, 'orders/explorar_productos.html', {
        'display_products': display_products,
        'categorias': categorias,
        'q': q,
        'categoria_id': categoria_id,
        'cart_count': len(cart['items']) if cart else 0,
        'store': store,
    })


@role_required('STORE_OWNER')
def ver_producto_orden(request, id):
    distributor = request.user.distributor
    product = get_object_or_404(
        Product.objects.filter(distributor=distributor, status=ProductStatus.ACTIVE)
        .select_related('category', 'brand')
        .prefetch_related('images', 'stock_levels__warehouse'),
        pk=id,
    )
    cart = request.session.get('cart')

    if request.method == 'POST':
        try:
            quantity = max(1, int(request.POST.get('quantity', 1)))
        except (ValueError, TypeError):
            quantity = 1

        cart, response = _ensure_cart(request, product.id, quantity)
        if response is not None:
            return response

        items = cart['items']
        for item in items:
            if item['product_id'] == product.id:
                item['quantity'] = quantity
                break
        else:
            items.append({'product_id': product.id, 'quantity': quantity})
        request.session.modified = True
        return redirect('explorar_productos')

    in_cart = 0
    if cart:
        for item in cart['items']:
            if item['product_id'] == product.id:
                in_cart = item['quantity']
                break

    return render(request, 'orders/ver_producto_orden.html', {
        'product': product,
        'price': product.current_price(),
        'stock': product.total_stock(),
        'stock_levels': product.stock_levels.select_related('warehouse').all(),
        'images': product.images.all(),
        'in_cart': in_cart,
        'cart_count': len(cart['items']) if cart else 0,
    })


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
            # Tier 4.5: warehouse is server-side, never client-supplied —
            # single default warehouse today, same pattern as
            # unit_price_at_time above.
            item.warehouse = Warehouse.get_or_create_default(pedido.store.distributor)
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
            # Tier 4.5: lock StockLevel(product, warehouse) rows — replaces
            # VendorInventory as the lock target. Stock is centralized (not
            # per-vendor, confirmed with the business 2026-07-21), so a
            # concurrent accept on ANY order touching the same product+
            # warehouse can't double-spend the same stock, tenant-wide
            # (NFR-03.1, NFR-03.3, UC-11 step 3-4). Accepted tradeoff: lock
            # contention widens from per-vendor to tenant-wide.
            niveles = {
                (nivel.product_id, nivel.warehouse_id): nivel
                for nivel in StockLevel.objects.select_for_update().filter(
                    warehouse_id__in={item.warehouse_id for item in items},
                    product_id__in=[item.product_id for item in items],
                )
            }
            errores = []
            for item in items:
                nivel = niveles.get((item.product_id, item.warehouse_id))
                disponible = nivel.quantity if nivel else 0
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
                nivel = niveles[(item.product_id, item.warehouse_id)]
                nivel.quantity -= item.quantity
                nivel.save(update_fields=['quantity'])
                deducciones.append({
                    'product': item.product.name,
                    'quantity_deducted': item.quantity,
                    'remaining_stock': nivel.quantity,
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


@role_required('VENDOR', 'DISTRIBUTOR')
def resolver_incidencia(request, id):
    if request.user.role == 'DISTRIBUTOR':
        pedido = get_object_or_404(
            Order, id=id,
            store__distributor=request.user.distributor,
            status=OrderStatus.DELIVERY_ISSUE,
        )
    else:
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
