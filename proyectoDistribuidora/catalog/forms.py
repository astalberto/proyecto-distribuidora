from django import forms
from .models import Store, Product, VendorInventory


class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['name', 'address', 'phone_number', 'distributor', 'owner', 'vendor']


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'unit_price', 'is_active', 'low_stock_threshold', 'distributor']


class VendorInventoryForm(forms.ModelForm):
    class Meta:
        model = VendorInventory
        fields = ['product', 'quantity']
