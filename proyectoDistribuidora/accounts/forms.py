from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm

from .models import Distributor, DistributorInvitation, User


class DistributorForm(forms.ModelForm):
    class Meta:
        model = Distributor
        fields = ['name', 'email']
        labels = {'name': 'Nombre', 'email': 'Correo electrónico'}


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


class DistributorInvitationForm(forms.Form):
    """Superuser issues a distributor self-registration invitation
    (superuser-only — see accounts/views.py:emitir_invitacion). target_email
    is optional: blank means link-only (anyone with the link can redeem it
    under any email); set means the join form's admin email must match it."""

    target_email = forms.EmailField(label='Correo del futuro administrador (opcional)', required=False)


class DistributorJoinForm(forms.Form):
    """Public self-registration form for a prospective distributor redeeming
    a DistributorInvitation — see accounts/views.py:registrar_distribuidor.
    Field-population logic mirrors DistributorOnboardingForm; kept separate
    since the two forms serve different callers (superuser vs. public) even
    though the fields are identical."""

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
        fields = ['email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].label = 'Correo electrónico'
        self.fields['password1'].label = 'Contraseña'
        self.fields['password2'].label = 'Confirmar contraseña'


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'role', 'is_active']
        labels = {
            'email': 'Correo electrónico',
            'role': 'Rol',
            'is_active': 'Activo',
        }


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
    store_latitude = forms.DecimalField(
        required=False, widget=forms.HiddenInput(), max_digits=9, decimal_places=6,
    )
    store_longitude = forms.DecimalField(
        required=False, widget=forms.HiddenInput(), max_digits=9, decimal_places=6,
    )
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
