from django.contrib import admin

from .models import Product, Store, VendorInventory

class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', )
    search_fields = ('name', 'address') 
admin.site.register(Store, StoreAdmin)  

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'unit_price')
    search_fields = ('name', 'description') 

    
admin.site.register(Product, ProductAdmin)  

class VendorInventoryAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'product', 'quantity')
    search_fields = ('vendor__username', 'product__name')   


admin.site.register(VendorInventory, VendorInventoryAdmin)  
# Register your models here.
