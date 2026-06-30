from django import forms
from .models import DeliveryConfirmation


class DeliveryConfirmationForm(forms.ModelForm):
    class Meta:
        model = DeliveryConfirmation
        fields = ['order', 'delivery_user', 'photo_public_id', 'confirmed_at']
