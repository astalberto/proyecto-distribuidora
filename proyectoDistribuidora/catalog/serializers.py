from rest_framework import serializers
from .models import Store, Product, VendorInventory

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['id', 'name', 'address', 'phone_number', 'distributor', 'owner', 'vendor']
        # distributor is stamped server-side from the caller's own tenant
        # (see catalog/api_views.py) — never client-supplied.
        read_only_fields = ['distributor']

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'unit_price', 'is_active', 'low_stock_threshold', 'distributor']
        read_only_fields = ['distributor']

class VendorInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorInventory
        fields = ['id', 'vendor', 'product', 'quantity']