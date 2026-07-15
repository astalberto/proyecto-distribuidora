from rest_framework import serializers
from .models import Store, Product, VendorInventory

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['id', 'name', 'address', 'phone_number', 'distributor', 'owner', 'vendor']

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'unit_price', 'is_active', 'low_stock_threshold', 'distributor']

class VendorInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorInventory
        fields = ['id', 'vendor', 'product', 'quantity']