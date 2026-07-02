from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index_orders'),
    path('new/', views.crear_pedido, name='crear_pedido'),
    path('items/<int:id>/edit/', views.editar_item_pedido, name='editar_item_pedido'),
    path('items/<int:id>/delete/', views.eliminar_item_pedido, name='eliminar_item_pedido'),
    path('<int:id>/', views.ver_pedido, name='ver_pedido'),
    path('<int:id>/edit/', views.editar_pedido, name='editar_pedido'),
    path('<int:id>/delete/', views.eliminar_pedido, name='eliminar_pedido'),
    path('<int:order_id>/items/new/', views.crear_item_pedido, name='crear_item_pedido'),
]
