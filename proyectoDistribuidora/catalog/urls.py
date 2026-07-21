from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index_catalog'),
    path('stores/new/', views.crear_tienda, name='crear_tienda'),
    path('stores/<int:id>/edit/', views.editar_tienda, name='editar_tienda'),
    path('stores/<int:id>/delete/', views.eliminar_tienda, name='eliminar_tienda'),

    path('categories/new/', views.crear_categoria, name='crear_categoria'),
    path('categories/<int:id>/edit/', views.editar_categoria, name='editar_categoria'),
    path('brands/new/', views.crear_marca, name='crear_marca'),
    path('brands/<int:id>/edit/', views.editar_marca, name='editar_marca'),

    path('products/new/', views.crear_producto, name='crear_producto'),
    path('products/<int:id>/edit/', views.editar_producto, name='editar_producto'),
    path('products/<int:id>/deactivate/', views.eliminar_producto, name='eliminar_producto'),
    path('products/<int:id>/reactivate/', views.reactivar_producto, name='reactivar_producto'),
    path('products/<int:id>/discontinue/', views.descontinuar_producto, name='descontinuar_producto'),
    path('products/<int:product_id>/discount/', views.gestionar_descuento, name='gestionar_descuento'),
    path('products/<int:product_id>/discount/remove/', views.quitar_descuento, name='quitar_descuento'),
    path('products/<int:product_id>/stock/', views.editar_stock, name='editar_stock'),
    path('products/import/', views.importar_productos, name='importar_productos'),
]
