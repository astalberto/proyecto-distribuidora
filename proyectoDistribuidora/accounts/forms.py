from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Distributor, User


class DistributorForm(forms.ModelForm):
    class Meta:
        model = Distributor
        fields = ['name', 'email']


class UserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['email', 'role', 'distributor']


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'role', 'distributor', 'is_active']
