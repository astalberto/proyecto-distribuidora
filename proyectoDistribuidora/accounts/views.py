import secrets
from datetime import timedelta

from django.contrib.auth import login as auth_login
from django.core.mail import send_mail
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone

from .decorators import role_required, superuser_required
from .models import Distributor, PasswordResetToken, Role, User
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
