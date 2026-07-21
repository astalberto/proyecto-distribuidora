from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm

from .models import Distributor, User


class DistributorForm(forms.ModelForm):
    class Meta:
        model = Distributor
        fields = ['name', 'email']


class DistributorOnboardingForm(forms.Form):
    """Creates a Distributor and its first DISTRIBUTOR-role user together
    (superuser-only — see accounts/views.py:crear_distribuidor). Combining
    them avoids the old two-step flow (create company, then separately use
    /admin/ to create its first admin user)."""

    distributor_name = forms.CharField(label='Nombre de la distribuidora', max_length=255)
    distributor_email = forms.EmailField(label='Correo de la distribuidora')
    admin_email = forms.EmailField(label='Correo del administrador')
    admin_password1 = forms.CharField(label='Contraseña', widget=forms.PasswordInput)
    admin_password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput)

    def clean_distributor_email(self):
        email = self.cleaned_data['distributor_email']
        if Distributor.objects.filter(email=email).exists():
            raise forms.ValidationError('Ya existe una distribuidora con este correo.')
        return email

    def clean_admin_email(self):
        email = self.cleaned_data['admin_email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Ya existe un usuario con este correo.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('admin_password1')
        p2 = cleaned.get('admin_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        if p1:
            password_validation.validate_password(p1)
        return cleaned


class UserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        # role is fixed by which "crear usuario" page the distributor is on
        # (see accounts/views.py:crear_usuario); distributor is the caller's
        # own tenant, set server-side — never a client-supplied field, or a
        # distributor admin could assign a user to a different tenant.
        fields = ['email']


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        # distributor is intentionally not editable here — reassigning a
        # user to a different tenant is not a DISTRIBUTOR-role action.
        fields = ['email', 'role', 'is_active']


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label='Correo electrónico')


class SetNewPasswordForm(forms.Form):
    new_password1 = forms.CharField(label='Nueva contraseña', widget=forms.PasswordInput)
    new_password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password1')
        p2 = cleaned.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        if p1:
            password_validation.validate_password(p1)
        return cleaned


class StoreOwnerSignupForm(forms.Form):
    """Self-registration for STORE_OWNER, reached via a distributor's
    invite link/QR code — the distributor is implicit in the URL token,
    never picked from a list. See accounts/views.py:registrar_tienda."""

    owner_email = forms.EmailField(label='Correo electrónico')
    owner_password1 = forms.CharField(label='Contraseña', widget=forms.PasswordInput)
    owner_password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput)
    store_name = forms.CharField(label='Nombre de la tienda', max_length=255)
    store_address = forms.CharField(label='Dirección', max_length=255, required=False)
    store_phone = forms.CharField(label='Teléfono', max_length=20, required=False)

    def clean_owner_email(self):
        email = self.cleaned_data['owner_email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Ya existe un usuario con este correo.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('owner_password1')
        p2 = cleaned.get('owner_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        if p1:
            password_validation.validate_password(p1)
        return cleaned
