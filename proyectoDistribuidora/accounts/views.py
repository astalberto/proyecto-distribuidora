from django.shortcuts import render, redirect
from .models import Distributor, User
from .forms import DistributorForm, UserCreateForm, UserEditForm


def index(request):
    distribuidores = Distributor.objects.all()
    return render(request, 'accounts/index.html', {'distribuidores': distribuidores})


# --- Distributor ---

def crear_distribuidor(request):
    if request.method == 'POST':
        formulario = DistributorForm(request.POST)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = DistributorForm()
    return render(request, 'accounts/crear_distribuidor.html', {'formulario': formulario})


def obtener_distribuidor(request, id):
    distribuidor = Distributor.objects.get(id=id)
    usuarios = distribuidor.users.all()
    return render(request, 'accounts/obtener_distribuidor.html', {
        'distribuidor': distribuidor,
        'usuarios': usuarios,
    })


def editar_distribuidor(request, id):
    distribuidor = Distributor.objects.get(id=id)
    if request.method == 'POST':
        formulario = DistributorForm(request.POST, instance=distribuidor)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = DistributorForm(instance=distribuidor)
    return render(request, 'accounts/editar_distribuidor.html', {
        'formulario': formulario,
        'distribuidor': distribuidor,
    })


def eliminar_distribuidor(request, id):
    Distributor.objects.get(id=id).delete()
    return redirect(index)


# --- User ---

def crear_usuario(request):
    if request.method == 'POST':
        formulario = UserCreateForm(request.POST)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = UserCreateForm()
    return render(request, 'accounts/crear_usuario.html', {'formulario': formulario})


def editar_usuario(request, id):
    usuario = User.objects.get(id=id)
    if request.method == 'POST':
        formulario = UserEditForm(request.POST, instance=usuario)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = UserEditForm(instance=usuario)
    return render(request, 'accounts/editar_usuario.html', {
        'formulario': formulario,
        'usuario': usuario,
    })


def eliminar_usuario(request, id):
    User.objects.get(id=id).delete()
    return redirect(index)
