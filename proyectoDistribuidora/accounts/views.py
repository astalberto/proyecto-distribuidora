import secrets
from datetime import timedelta

from django.contrib.auth import login as auth_login
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.http import Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone

from catalog.models import ProductStatus, StockLevel, Store
from orders.models import Order, OrderStatus
from .decorators import role_required, superuser_required
from .models import Distributor, Notification, PasswordResetToken, Role, User
from .forms import (
    DistributorForm,
    DistributorOnboardingForm,
    PasswordResetRequestForm,
    SetNewPasswordForm,
    StoreOwnerSignupForm,
    UserCreateForm,
    UserEditForm,
)


@role_required('DISTRIBUTOR')
def index(request):
    distribuidor = request.user.distributor
    usuarios = distribuidor.users.all() if distribuidor else User.objects.none()
    return render(request, 'accounts/index.html', {
        'distribuidor': distribuidor,
        'usuarios': usuarios,
    })


# --- Distributor — platform onboarding, precedes any DISTRIBUTOR user existing ---

@superuser_required
def crear_distribuidor(request):
    """Onboards a new Distributor and its first DISTRIBUTOR-role user
    together, in one atomic step — see forms.DistributorOnboardingForm."""
    if request.method == 'POST':
        formulario = DistributorOnboardingForm(request.POST)
        if formulario.is_valid():
            with transaction.atomic():
                distribuidor = Distributor.objects.create(
                    name=formulario.cleaned_data['distributor_name'],
                    email=formulario.cleaned_data['distributor_email'],
                )
                User.objects.create_user(
                    email=formulario.cleaned_data['admin_email'],
                    password=formulario.cleaned_data['admin_password1'],
                    role=Role.DISTRIBUTOR,
                    distributor=distribuidor,
                )
            return redirect(index)
    else:
        formulario = DistributorOnboardingForm()
    return render(request, 'accounts/crear_distribuidor.html', {'formulario': formulario})


@superuser_required
def obtener_distribuidor(request, id):
    distribuidor = get_object_or_404(Distributor, id=id)
    usuarios = distribuidor.users.all()
    return render(request, 'accounts/obtener_distribuidor.html', {
        'distribuidor': distribuidor,
        'usuarios': usuarios,
    })


@superuser_required
def editar_distribuidor(request, id):
    distribuidor = get_object_or_404(Distributor, id=id)
    if request.method == 'POST':
        formulario = DistributorForm(request.POST, instance=distribuidor)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = DistributorForm(instance=distribuidor)
    return render(request, 'accounts/editar_distribuidor.html', {
        'formulario': formulario,
        'distribuidor': distribuidor,
    })


@superuser_required
def eliminar_distribuidor(request, id):
    get_object_or_404(Distributor, id=id).delete()
    return redirect(index)


# --- User — scoped to the caller's own distributor ---

@role_required('DISTRIBUTOR')
def crear_usuario(request, role):
    role_label = dict(Role.choices).get(role)
    if role_label is None:
        raise Http404('Rol desconocido')

    if request.method == 'POST':
        formulario = UserCreateForm(request.POST)
        if formulario.is_valid():
            usuario = formulario.save(commit=False)
            usuario.role = role
            # Tenant isolation: the caller's own distributor, never client-supplied.
            usuario.distributor = request.user.distributor
            usuario.save()
            return redirect(index)
    else:
        formulario = UserCreateForm()
    return render(request, 'accounts/crear_usuario.html', {
        'formulario': formulario,
        'role': role,
        'role_label': role_label,
    })


@role_required('DISTRIBUTOR')
def editar_usuario(request, id):
    usuario = get_object_or_404(User, id=id, distributor=request.user.distributor)
    if request.method == 'POST':
        formulario = UserEditForm(request.POST, instance=usuario)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = UserEditForm(instance=usuario)
    return render(request, 'accounts/editar_usuario.html', {
        'formulario': formulario,
        'usuario': usuario,
    })


@role_required('DISTRIBUTOR')
def eliminar_usuario(request, id):
    get_object_or_404(User, id=id, distributor=request.user.distributor).delete()
    return redirect(index)


@role_required('DISTRIBUTOR')
def dashboard(request):
    """FR-08.1 (orders by status), FR-08.2 (filter by date/vendor/store/
    status), FR-08.3 (stock per product per vendor), FR-08.4 (summary
    metrics, filterable by vendor and period).

    Every query is freshly evaluated on every request — the requirement is
    "reflects the latest state within one page load", not real-time push,
    so a plain page load already satisfies it."""
    distribuidor = request.user.distributor

    pedidos = Order.objects.filter(store__distributor=distribuidor)

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    vendor_id = request.GET.get('vendor', '')
    store_id = request.GET.get('store', '')
    status = request.GET.get('status', '')

    if date_from:
        pedidos = pedidos.filter(created_at__date__gte=date_from)
    if date_to:
        pedidos = pedidos.filter(created_at__date__lte=date_to)
    if vendor_id:
        pedidos = pedidos.filter(vendor_id=vendor_id)
    if store_id:
        pedidos = pedidos.filter(store_id=store_id)
    if status:
        pedidos = pedidos.filter(status=status)

    ordenes_por_estado = pedidos.values('status').annotate(total=Count('id')).order_by('status')
    pedidos_recientes = pedidos.select_related('store', 'vendor').order_by('-created_at')[:50]

    # Average fulfillment time: for a CONFIRMED order, updated_at is exactly
    # when it reached that terminal state (whether via the direct
    # confirm-receipt path or the report-issue -> resolve path — either way
    # the final save that sets status=CONFIRMED is the last one).
    tiempo_promedio = pedidos.filter(status=OrderStatus.CONFIRMED).annotate(
        duracion=ExpressionWrapper(F('updated_at') - F('created_at'), output_field=DurationField())
    ).aggregate(promedio=Avg('duracion'))['promedio']

    metricas = {
        'total': pedidos.count(),
        'fulfilled': pedidos.filter(status=OrderStatus.CONFIRMED).count(),
        'rejected': pedidos.filter(status=OrderStatus.REJECTED).count(),
        'tiempo_promedio': tiempo_promedio,
    }

    # Tier 4.5: replaces the per-vendor VendorInventory table with
    # per-warehouse StockLevel (stock is centralized, not per-vendor).
    inventario = (
        StockLevel.objects.filter(
            product__distributor=distribuidor, product__status=ProductStatus.ACTIVE
        )
        .select_related('warehouse', 'product')
        .order_by('product__name', 'warehouse__name')
    )
    stock_bajo_count = sum(
        1 for inv in inventario if inv.quantity < inv.product.low_stock_threshold
    )

    return render(request, 'accounts/dashboard.html', {
        'distribuidor': distribuidor,
        'ordenes_por_estado': ordenes_por_estado,
        'pedidos_recientes': pedidos_recientes,
        'metricas': metricas,
        'inventario': inventario,
        'stock_bajo_count': stock_bajo_count,
        'vendedores': User.objects.filter(distributor=distribuidor, role=Role.VENDOR),
        'tiendas': Store.objects.filter(distributor=distribuidor),
        'status_choices': OrderStatus.choices,
        'filtros': {
            'date_from': date_from,
            'date_to': date_to,
            'vendor': vendor_id,
            'store': store_id,
            'status': status,
        },
    })


@role_required('DISTRIBUTOR')
def regenerar_invite_token(request):
    """Revokes the distributor's current store-owner invite link and issues
    a new one (e.g. if the old link/QR was compromised)."""
    if request.method == 'POST' and request.user.distributor:
        request.user.distributor.regenerate_invite_token()
    return redirect(index)


# --- Store owner self-registration — unauthenticated, reached via a
# distributor's invite link/QR code (no public distributor picker) ---

def registrar_tienda(request, token):
    from catalog.models import Store  # local import: avoids a circular import with catalog.models

    distribuidor = get_object_or_404(Distributor, invite_token=token)

    if request.method == 'POST':
        formulario = StoreOwnerSignupForm(request.POST)
        if formulario.is_valid():
            with transaction.atomic():
                propietario = User.objects.create_user(
                    email=formulario.cleaned_data['owner_email'],
                    password=formulario.cleaned_data['owner_password1'],
                    role=Role.STORE_OWNER,
                    distributor=distribuidor,
                )
                Store.objects.create(
                    name=formulario.cleaned_data['store_name'],
                    address=formulario.cleaned_data['store_address'],
                    phone_number=formulario.cleaned_data['store_phone'],
                    distributor=distribuidor,
                    owner=propietario,
                    # vendor intentionally left unassigned — the distributor
                    # assigns one afterward (DR-01); until then, order
                    # placement shows the existing "sin vendedor asignado" message.
                )
            auth_login(request, propietario)
            return redirect('home')
    else:
        formulario = StoreOwnerSignupForm()
    return render(request, 'accounts/registrar_tienda.html', {
        'formulario': formulario,
        'distribuidor': distribuidor,
    })


# --- Password reset — unauthenticated by design (FR-01.3, FR-01.4, FR-01.6) ---

def solicitar_reset_password(request):
    if request.method == 'POST':
        formulario = PasswordResetRequestForm(request.POST)
        if formulario.is_valid():
            email = formulario.cleaned_data['email']
            usuario = User.objects.filter(email=email).first()
            if usuario is not None:
                token = secrets.token_urlsafe(32)
                PasswordResetToken.objects.create(
                    user=usuario,
                    token=token,
                    expires_at=timezone.now() + timedelta(hours=1),
                )
                reset_url = request.build_absolute_uri(
                    reverse('confirmar_reset_password', args=[token])
                )
                send_mail(
                    subject='Restablecer contraseña — ISBER Solutions',
                    message=(
                        'Usa este enlace para restablecer tu contraseña '
                        f'(válido por 1 hora): {reset_url}'
                    ),
                    from_email=None,
                    recipient_list=[email],
                )
            # Same response whether or not the email exists — prevents
            # user enumeration (UC-03 Alt Flow A3).
            return render(request, 'accounts/password_reset_solicitado.html')
    else:
        formulario = PasswordResetRequestForm()
    return render(request, 'accounts/solicitar_reset_password.html', {'formulario': formulario})


def confirmar_reset_password(request, token):
    reset_token = get_object_or_404(PasswordResetToken, token=token)

    if reset_token.used_at is not None:
        return render(request, 'accounts/reset_password_invalido.html', {
            'motivo': 'este enlace ya fue utilizado',
        })
    if reset_token.expires_at < timezone.now():
        return render(request, 'accounts/reset_password_invalido.html', {
            'motivo': 'el enlace ha expirado, solicita uno nuevo',
        })

    if request.method == 'POST':
        formulario = SetNewPasswordForm(request.POST)
        if formulario.is_valid():
            usuario = reset_token.user
            usuario.set_password(formulario.cleaned_data['new_password1'])
            usuario.save(update_fields=['password'])
            reset_token.used_at = timezone.now()
            reset_token.save(update_fields=['used_at'])
            return redirect('login')
    else:
        formulario = SetNewPasswordForm()
    return render(request, 'accounts/confirmar_reset_password.html', {'formulario': formulario})


# --- Notifications (US-16) — every role can receive them, not just STORE_OWNER ---

@role_required(*Role.values)
def notificaciones(request):
    notifs = request.user.notifications.select_related('order').all()
    return render(request, 'accounts/notificaciones.html', {'notificaciones': notifs})


@role_required(*Role.values)
def marcar_notificacion_leida(request, id):
    notif = get_object_or_404(Notification, id=id, user=request.user)
    if request.method == 'POST':
        notif.is_read = True
        notif.save(update_fields=['is_read'])
    return redirect('notificaciones')


@role_required(*Role.values)
def marcar_todas_leidas(request):
    if request.method == 'POST':
        request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('notificaciones')
