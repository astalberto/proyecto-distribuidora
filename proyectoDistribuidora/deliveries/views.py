from django.shortcuts import render, redirect
from .models import DeliveryConfirmation
from .forms import DeliveryConfirmationForm


def index(request):
    return render(request, 'deliveries/index.html', {
        'confirmaciones': DeliveryConfirmation.objects.all(),
    })


def crear_confirmacion(request):
    if request.method == 'POST':
        formulario = DeliveryConfirmationForm(request.POST)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = DeliveryConfirmationForm()
    return render(request, 'deliveries/crear_confirmacion.html', {'formulario': formulario})


def editar_confirmacion(request, id):
    confirmacion = DeliveryConfirmation.objects.get(id=id)
    if request.method == 'POST':
        formulario = DeliveryConfirmationForm(request.POST, instance=confirmacion)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = DeliveryConfirmationForm(instance=confirmacion)
    return render(request, 'deliveries/editar_confirmacion.html', {
        'formulario': formulario,
        'confirmacion': confirmacion,
    })


def eliminar_confirmacion(request, id):
    DeliveryConfirmation.objects.get(id=id).delete()
    return redirect(index)
