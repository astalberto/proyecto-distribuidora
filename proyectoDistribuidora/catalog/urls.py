from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index_catalog'),
    path('stores/new/', views.crear_tienda, name='crear_tienda'),
    path('stores/<int:id>/edit/', views.editar_tienda, name='editar_tienda'),
    path('stores/<int:id>/delete/', views.eliminar_tienda, name='eliminar_tienda'),
    path('products/new/', views.crear_producto, name='crear_producto'),
    path('products/<int:id>/edit/', views.editar_producto, name='editar_producto'),
    path('products/<int:id>/deactivate/', views.eliminar_producto, name='eliminar_producto'),
    path('products/<int:id>/reactivate/', views.reactivar_producto, name='reactivar_producto'),
    path('inventory/assign/<int:vendor_id>/', views.crear_inventario, name='crear_inventario'),
    path('inventory/<int:id>/edit/', views.editar_inventario, name='editar_inventario'),
    path('inventory/<int:id>/delete/', views.eliminar_inventario, name='eliminar_inventario'),
]
