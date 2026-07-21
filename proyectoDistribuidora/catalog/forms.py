from django import forms
from accounts.models import User
from .models import Store, Product, VendorInventory


class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        # distributor is set server-side from request.user.distributor, not
        # client-supplied — see catalog/views.py.
        fields = ['name', 'address', 'phone_number', 'owner', 'vendor']

    def __init__(self, *args, distributor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if distributor is not None:
            self.fields['owner'].queryset = User.objects.filter(distributor=distributor)
            self.fields['vendor'].queryset = User.objects.filter(distributor=distributor)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        # distributor is set server-side from request.user.distributor, not
        # client-supplied — see catalog/views.py.
        fields = ['name', 'description', 'unit_price', 'is_active', 'low_stock_threshold']


class VendorInventoryForm(forms.ModelForm):
    class Meta:
        model = VendorInventory
        fields = ['product', 'quantity']

    def __init__(self, *args, distributor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if distributor is not None:
            self.fields['product'].queryset = Product.objects.filter(distributor=distributor)
