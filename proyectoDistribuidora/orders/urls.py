from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index_orders'),
    path('crear/pedido', views.crear_pedido, name='crear_pedido'),
    path('ver/pedido/<int:id>', views.ver_pedido, name='ver_pedido'),
    path('editar/pedido/<int:id>', views.editar_pedido, name='editar_pedido'),
    path('eliminar/pedido/<int:id>', views.eliminar_pedido, name='eliminar_pedido'),
    path('crear/item/<int:order_id>', views.crear_item_pedido, name='crear_item_pedido'),
    path('editar/item/<int:id>', views.editar_item_pedido, name='editar_item_pedido'),
    path('eliminar/item/<int:id>', views.eliminar_item_pedido, name='eliminar_item_pedido'),
]
