from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index_deliveries'),
    path('crear/confirmacion', views.crear_confirmacion, name='crear_confirmacion'),
    path('editar/confirmacion/<int:id>', views.editar_confirmacion, name='editar_confirmacion'),
    path('eliminar/confirmacion/<int:id>', views.eliminar_confirmacion, name='eliminar_confirmacion'),
]
