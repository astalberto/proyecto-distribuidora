from django.contrib import admin

from .models import Product, Store, VendorInventory

class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'owner', 'distributor')
    search_fields = ('name', 'address', 'phone_number', 'distributor__name')
    list_filter = ('distributor',)

admin.site.register(Store, StoreAdmin)


class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit_price', 'is_active', 'low_stock_threshold', 'distributor')
    search_fields = ('name', 'description')
    list_filter = ('is_active', 'distributor')

admin.site.register(Product, ProductAdmin)


class VendorInventoryAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'product', 'quantity')
    search_fields = ('vendor__email', 'product__name')

admin.site.register(VendorInventory, VendorInventoryAdmin)
