from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.index, name='index_accounts'),
    path('distributors/<int:id>/', views.obtener_distribuidor, name='obtener_distribuidor'),
    path('distributors/new/', views.crear_distribuidor, name='crear_distribuidor'),
    path('distributors/<int:id>/edit/', views.editar_distribuidor, name='editar_distribuidor'),
    path('distributors/<int:id>/delete/', views.eliminar_distribuidor, name='eliminar_distribuidor'),
    path('users/new/<str:role>/', views.crear_usuario, name='crear_usuario'),
    path('users/<int:id>/edit/', views.editar_usuario, name='editar_usuario'),
    path('users/<int:id>/delete/', views.eliminar_usuario, name='eliminar_usuario'),
    path('password-reset/', views.solicitar_reset_password, name='solicitar_reset_password'),
    path('password-reset/<str:token>/', views.confirmar_reset_password, name='confirmar_reset_password'),
    path('invite-token/regenerate/', views.regenerar_invite_token, name='regenerar_invite_token'),
    path('join/<str:token>/', views.registrar_tienda, name='registrar_tienda'),
]
