from django import forms
from .models import Distributor, User


class DistributorForm(forms.ModelForm):
    class Meta:
        model = Distributor
        fields = ['name', 'email']


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'password_hash', 'role', 'distributor']
