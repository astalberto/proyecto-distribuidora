from django.shortcuts import render, redirect
from .models import Order, OrderItem
from .forms import OrderForm, OrderItemForm


def index(request):
    return render(request, 'orders/index.html', {'pedidos': Order.objects.all()})


def crear_pedido(request):
    if request.method == 'POST':
        formulario = OrderForm(request.POST)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = OrderForm()
    return render(request, 'orders/crear_pedido.html', {'formulario': formulario})


def ver_pedido(request, id):
    pedido = Order.objects.get(id=id)
    return render(request, 'orders/ver_pedido.html', {
        'pedido': pedido,
        'items': pedido.items.all(),
    })


def editar_pedido(request, id):
    pedido = Order.objects.get(id=id)
    if request.method == 'POST':
        formulario = OrderForm(request.POST, instance=pedido)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = OrderForm(instance=pedido)
    return render(request, 'orders/editar_pedido.html', {
        'formulario': formulario,
        'pedido': pedido,
    })


def eliminar_pedido(request, id):
    Order.objects.get(id=id).delete()
    return redirect(index)


def crear_item_pedido(request, order_id):
    pedido = Order.objects.get(id=order_id)
    if request.method == 'POST':
        formulario = OrderItemForm(request.POST)
        if formulario.is_valid():
            item = formulario.save(commit=False)
            item.order = pedido
            item.save()
            return redirect('ver_pedido', id=order_id)
    else:
        formulario = OrderItemForm()
    return render(request, 'orders/crear_item_pedido.html', {
        'formulario': formulario,
        'pedido': pedido,
    })


def editar_item_pedido(request, id):
    item = OrderItem.objects.get(id=id)
    if request.method == 'POST':
        formulario = OrderItemForm(request.POST, instance=item)
        if formulario.is_valid():
            formulario.save()
            return redirect('ver_pedido', id=item.order.id)
    else:
        formulario = OrderItemForm(instance=item)
    return render(request, 'orders/editar_item_pedido.html', {
        'formulario': formulario,
        'item': item,
    })


def eliminar_item_pedido(request, id):
    item = OrderItem.objects.get(id=id)
    order_id = item.order.id
    item.delete()
    return redirect('ver_pedido', id=order_id)
