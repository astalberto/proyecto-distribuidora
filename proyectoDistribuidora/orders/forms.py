from django import forms
from .models import Order, OrderItem


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        # vendor is omitted — auto-populated from store.vendor in the view (DR-01)
        fields = ['store', 'status', 'previous_order', 'rejection_reason']


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'unit_price_at_time']
