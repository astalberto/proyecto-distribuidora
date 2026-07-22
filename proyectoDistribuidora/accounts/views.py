import secrets
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.http import Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone

from audit.models import AuditLog
from catalog.models import ProductStatus, StockLevel, Store
from orders.models import Order, OrderStatus
from .decorators import role_required, superuser_required
from .models import Distributor, DistributorInvitation, Notification, PasswordResetToken, Role, TenantStatus, User
from .forms import (
    DistributorForm,
    DistributorInvitationForm,
    DistributorJoinForm,
    DistributorOnboardingForm,
    PasswordResetRequestForm,
    SetNewPasswordForm,
    StoreOwnerSignupForm,
    UserCreateForm,
    UserEditForm,
)


def home_view(request):
    if not request.user.is_authenticated:
        return render(request, 'home.html')
    if request.user.is_superuser or request.user.role == Role.SUPER_ADMIN:
        return redirect('operator_dashboard')
    role = request.user.role
    if role == Role.DISTRIBUTOR:
        return redirect('distributor_dashboard')
    if role in (Role.VENDOR, Role.STORE_OWNER):
        return redirect('index_orders')
    if role == Role.DELIVERY:
        return redirect('index_deliveries')
    return render(request, 'home.html')


# --- Operator views — platform-level, gated by @superuser_required ---

@superuser_required
def operator_dashboard(request):
    distribuidores = (
        Distributor.objects
        .annotate(user_count=Count('users'))
        .order_by('status', 'name')
    )
    totales = {s.value: 0 for s in TenantStatus}
    for d in distribuidores:
        if d.status in totales:
            totales[d.status] += 1
    return render(request, 'accounts/operator_dashboard.html', {
        'distribuidores': distribuidores,
        'totales': totales,
        'TenantStatus': TenantStatus,
    })


@superuser_required
def operator_tenant_detail(request, id):
    distribuidor = get_object_or_404(Distributor, id=id)
    usuarios = distribuidor.users.all()
    audit_entries = AuditLog.objects.filter(
        user__distributor=distribuidor
    ).select_related('user').order_by('-id')[:20]
    return render(request, 'accounts/operator_tenant_detail.html', {
        'distribuidor': distribuidor,
        'usuarios': usuarios,
        'audit_entries': audit_entries,
        'TenantStatus': TenantStatus,
    })


@superuser_required
def operator_activate_tenant(request, id):
    if request.method != 'POST':
        return redirect('operator_tenant_detail', id=id)
    distribuidor = get_object_or_404(Distributor, id=id)
    distribuidor.status = TenantStatus.ACTIVE
    distribuidor.save(update_fields=['status'])
    AuditLog.objects.create(
        user=request.user,
        action='tenant_activated',
        entity_type='Distributor',
        entity_id=str(distribuidor.id),
        details={'by': request.user.email},
    )
    messages.success(request, f'Distribuidor "{distribuidor.name}" activado.')
    return redirect('operator_tenant_detail', id=id)


@superuser_required
def operator_suspend_tenant(request, id):
    if request.method != 'POST':
        return redirect('operator_tenant_detail', id=id)
    distribuidor = get_object_or_404(Distributor, id=id)
    distribuidor.status = TenantStatus.SUSPENDED
    distribuidor.save(update_fields=['status'])
    AuditLog.objects.create(
        user=request.user,
        action='tenant_suspended',
        entity_type='Distributor',
        entity_id=str(distribuidor.id),
        details={'by': request.user.email},
    )
    messages.success(request, f'Distribuidor "{distribuidor.name}" suspendido.')
    return redirect('operator_tenant_detail', id=id)


@role_required('DISTRIBUTOR')
def index(request):
    distribuidor = request.user.distributor
    usuarios = distribuidor.users.all() if distribuidor else User.objects.none()
    tiendas = Store.objects.filter(distributor=distribuidor).select_related('owner', 'vendor') if distribuidor else Store.objects.none()
    return render(request, 'accounts/index.html', {
        'distribuidor': distribuidor,
        'usuarios': usuarios,
        'tiendas': tiendas,
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
            # Eng-review Finding A1: redirect(index) used to send the
            # superuser into a 403 wall — index is @role_required
            # ('DISTRIBUTOR') and a superuser has role=''. Send them
            # somewhere they can actually reach instead.
            return redirect('invitaciones')
    else:
        formulario = DistributorOnboardingForm()
    return render(request, 'accounts/crear_distribuidor.html', {'formulario': formulario})


# --- Distributor self-service invitations (ISBEN roadmap item 3) ---

@superuser_required
def emitir_invitacion(request):
    """Issues a single-use DistributorInvitation. Superuser-only: Distributor
    is the top of the tenant hierarchy, so there's no higher-level tenant to
    scope this action to — see docs/TODOS.md Tier 6 item 3."""
    if request.method == 'POST':
        formulario = DistributorInvitationForm(request.POST)
        if formulario.is_valid():
            invitacion = DistributorInvitation.objects.create(
                token=secrets.token_urlsafe(32),
                target_email=formulario.cleaned_data['target_email'],
                expires_at=timezone.now() + timedelta(days=7),
                created_by=request.user,
            )
            AuditLog.objects.create(
                user=request.user,
                action='invitation_issued',
                entity_type='DistributorInvitation',
                entity_id=str(invitacion.id),
                details={'target_email': invitacion.target_email},
            )
            join_url = request.build_absolute_uri(
                reverse('registrar_distribuidor', args=[invitacion.token])
            )
            if invitacion.target_email:
                try:
                    send_mail(
                        subject='Invitación — ISBEN Solutions',
                        message=(
                            'Has sido invitado a registrar tu distribuidora en '
                            f'ISBEN Solutions. Usa este enlace (válido por 7 días): {join_url}'
                        ),
                        from_email=None,
                        recipient_list=[invitacion.target_email],
                    )
                    messages.success(request, 'Invitación creada y enviada por correo.')
                except Exception:
                    messages.warning(
                        request,
                        'Invitación creada, pero el correo no pudo enviarse — '
                        f'comparte este enlace manualmente: {join_url}',
                    )
            else:
                messages.success(request, f'Invitación creada — comparte este enlace: {join_url}')
            return redirect('invitaciones')
    else:
        formulario = DistributorInvitationForm()
    return render(request, 'accounts/emitir_invitacion.html', {'formulario': formulario})


@superuser_required
def invitaciones(request):
    lista = DistributorInvitation.objects.select_related('created_by').order_by('-created_at')
    return render(request, 'accounts/invitaciones.html', {'invitaciones': lista})


@superuser_required
def revocar_invitacion(request, id):
    invitacion = get_object_or_404(DistributorInvitation, id=id)
    if request.method == 'POST':
        if invitacion.revoked_at is None:
            invitacion.revoked_at = timezone.now()
            invitacion.save(update_fields=['revoked_at'])
        AuditLog.objects.create(
            user=request.user,
            action='invitation_revoked',
            entity_type='DistributorInvitation',
            entity_id=str(invitacion.id),
        )
    return redirect('invitaciones')


# --- Distributor self-registration — unauthenticated, reached via a
# superuser-issued invitation link (no public distributor picker) ---

def registrar_distribuidor(request, token):
    invitacion = get_object_or_404(DistributorInvitation, token=token)

    # Optimistic pre-checks for a friendly GET response — the authoritative
    # check happens again after acquiring the lock, right before creating
    # anything (see the atomic block below).
    if invitacion.revoked_at is not None:
        return render(request, 'accounts/invitacion_invalida.html', {
            'motivo': 'esta invitación fue revocada',
        })
    if invitacion.used_at is not None:
        return render(request, 'accounts/invitacion_invalida.html', {
            'motivo': 'este enlace ya fue utilizado',
        })
    if invitacion.is_expired():
        return render(request, 'accounts/invitacion_invalida.html', {
            'motivo': 'el enlace ha expirado, solicita uno nuevo',
        })

    if request.method == 'POST':
        formulario = DistributorJoinForm(request.POST)
        if formulario.is_valid():
            if (
                invitacion.target_email
                and formulario.cleaned_data['admin_email'].lower() != invitacion.target_email.lower()
            ):
                formulario.add_error('admin_email', 'El correo no coincide con la invitación.')
            else:
                # Eng-review Finding B1 (CRITICAL): lock acquisition, the
                # re-check, entity creation, and the used_at write all live
                # in ONE atomic block — never split into a separate
                # transaction, or two concurrent redemptions of the same
                # token could both create a Distributor before either marks
                # it used. Mirrors orders.views.aceptar_pedido's single-
                # atomic-block lock pattern exactly. Copies
                # DistributorOnboardingForm's field-population logic
                # directly rather than calling crear_distribuidor (which
                # opens its own independent transaction.atomic()).
                with transaction.atomic():
                    bloqueada = DistributorInvitation.objects.select_for_update().get(id=invitacion.id)
                    if not bloqueada.is_usable():
                        # Lost the race — another request already redeemed
                        # or revoked it first.
                        return render(request, 'accounts/invitacion_invalida.html', {
                            'motivo': 'este enlace ya no está disponible',
                        })
                    distribuidor = Distributor.objects.create(
                        name=formulario.cleaned_data['distributor_name'],
                        email=formulario.cleaned_data['distributor_email'],
                    )
                    admin = User.objects.create_user(
                        email=formulario.cleaned_data['admin_email'],
                        password=formulario.cleaned_data['admin_password1'],
                        role=Role.DISTRIBUTOR,
                        distributor=distribuidor,
                    )
                    bloqueada.used_at = timezone.now()
                    bloqueada.save(update_fields=['used_at'])
                    AuditLog.objects.create(
                        user=admin,
                        action='invitation_redeemed',
                        entity_type='DistributorInvitation',
                        entity_id=str(bloqueada.id),
                        details={'distributor_id': distribuidor.id},
                    )
                auth_login(request, admin)
                return redirect('distributor_dashboard')
    else:
        formulario = DistributorJoinForm()
    return render(request, 'accounts/registrar_distribuidor.html', {
        'formulario': formulario,
        'invitacion': invitacion,
    })


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
            if role == Role.STORE_OWNER:
                return redirect('crear_tienda')
            return redirect('index_accounts')
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
                    latitude=formulario.cleaned_data.get('store_latitude'),
                    longitude=formulario.cleaned_data.get('store_longitude'),
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
                    subject='Restablecer contraseña — ISBEN Solutions',
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
    unread = list(
        request.user.notifications.filter(is_read=False)
        .select_related('order')
        .order_by('-created_at')
    )
    read_recent = list(
        request.user.notifications.filter(is_read=True)
        .select_related('order')
        .order_by('-created_at')[:10]
    )
    return render(request, 'accounts/notificaciones.html', {
        'notificaciones': unread + read_recent,
    })


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
