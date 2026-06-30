from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index_catalog'),
    path('crear/tienda', views.crear_tienda, name='crear_tienda'),
    path('editar/tienda/<int:id>', views.editar_tienda, name='editar_tienda'),
    path('eliminar/tienda/<int:id>', views.eliminar_tienda, name='eliminar_tienda'),
    path('crear/producto', views.crear_producto, name='crear_producto'),
    path('editar/producto/<int:id>', views.editar_producto, name='editar_producto'),
    path('eliminar/producto/<int:id>', views.eliminar_producto, name='eliminar_producto'),
    path('crear/inventario/<int:vendor_id>', views.crear_inventario, name='crear_inventario'),
    path('editar/inventario/<int:id>', views.editar_inventario, name='editar_inventario'),
    path('eliminar/inventario/<int:id>', views.eliminar_inventario, name='eliminar_inventario'),
]
