from django import forms
from .models import Order, OrderItem


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['store', 'vendor', 'status', 'previous_order']


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'unit_price_at_time']
