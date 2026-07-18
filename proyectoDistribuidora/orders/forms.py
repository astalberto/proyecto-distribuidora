from django import forms
from catalog.models import Store, Product
from .models import Order, OrderItem


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        # status/previous_order/rejection_reason are never client-editable —
        # status only changes through the dedicated accept/reject/dispatch/
        # cancel views; previous_order and rejection_reason are set
        # server-side by those views, not by the store owner.
        fields = ['store']

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.fields['store'].queryset = Store.objects.filter(owner=owner)


class ReportarIncidenciaForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['issue_description']
        widgets = {'issue_description': forms.Textarea(attrs={'rows': 4})}
        labels = {'issue_description': 'Describe el problema'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # blank=True on the model allows orders with no issue; a submitted
        # report itself must not be empty.
        self.fields['issue_description'].required = True


class ResolverIncidenciaForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['resolution_notes']
        widgets = {'resolution_notes': forms.Textarea(attrs={'rows': 4})}
        labels = {'resolution_notes': 'Notas de resolución'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resolution_notes'].required = True


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        # unit_price_at_time is never client-editable — the view snapshots
        # it server-side from Product.unit_price at save time (FR-05.4).
        fields = ['product', 'quantity']

    def __init__(self, *args, vendor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if vendor is not None:
            # FR-05.3: only products actually stocked by the order's
            # assigned vendor can be ordered.
            self.fields['product'].queryset = Product.objects.filter(
                inventory__vendor=vendor, is_active=True
            ).distinct()
