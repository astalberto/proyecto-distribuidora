from django.contrib import admin
from .models import *

class DistribuidorAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')
    search_fields = ('name', 'email')   

admin.site.register(Distributor, DistribuidorAdmin)

class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'role', 'distributor')
    search_fields = ('email',)
    list_filter = ('role',)
    
admin.site.register(User, UserAdmin)
# Register your models here.
