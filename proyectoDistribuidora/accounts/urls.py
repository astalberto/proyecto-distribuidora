from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index_accounts'),
    path('distribuidor/<int:id>/', views.obtener_distribuidor, name='obtener_distribuidor'),
    path('crear/distribuidor', views.crear_distribuidor, name='crear_distribuidor'),
    path('editar/distribuidor/<int:id>', views.editar_distribuidor, name='editar_distribuidor'),
    path('eliminar/distribuidor/<int:id>', views.eliminar_distribuidor, name='eliminar_distribuidor'),
    path('crear/usuario', views.crear_usuario, name='crear_usuario'),
    path('editar/usuario/<int:id>', views.editar_usuario, name='editar_usuario'),
    path('eliminar/usuario/<int:id>', views.eliminar_usuario, name='eliminar_usuario'),
]
