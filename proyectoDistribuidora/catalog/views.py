from django.shortcuts import render, redirect
from .models import Store, Product, VendorInventory
from .forms import StoreForm, ProductForm, VendorInventoryForm
from accounts.models import User


def index(request):
    return render(request, 'catalog/index.html', {
        'tiendas': Store.objects.all(),
        'productos': Product.objects.all(),
        'inventarios': VendorInventory.objects.all(),
    })


# --- Store ---

def crear_tienda(request):
    if request.method == 'POST':
        formulario = StoreForm(request.POST)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = StoreForm()
    return render(request, 'catalog/crear_tienda.html', {'formulario': formulario})


def editar_tienda(request, id):
    tienda = Store.objects.get(id=id)
    if request.method == 'POST':
        formulario = StoreForm(request.POST, instance=tienda)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = StoreForm(instance=tienda)
    return render(request, 'catalog/editar_tienda.html', {
        'formulario': formulario,
        'tienda': tienda,
    })


def eliminar_tienda(request, id):
    Store.objects.get(id=id).delete()
    return redirect(index)


# --- Product ---

def crear_producto(request):
    if request.method == 'POST':
        formulario = ProductForm(request.POST)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = ProductForm()
    return render(request, 'catalog/crear_producto.html', {'formulario': formulario})


def editar_producto(request, id):
    producto = Product.objects.get(id=id)
    if request.method == 'POST':
        formulario = ProductForm(request.POST, instance=producto)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = ProductForm(instance=producto)
    return render(request, 'catalog/editar_producto.html', {
        'formulario': formulario,
        'producto': producto,
    })


def eliminar_producto(request, id):
    Product.objects.get(id=id).delete()
    return redirect(index)


# --- VendorInventory — vendor injected via URL ---

def crear_inventario(request, vendor_id):
    vendor = User.objects.get(id=vendor_id)
    if request.method == 'POST':
        formulario = VendorInventoryForm(request.POST)
        if formulario.is_valid():
            inv = formulario.save(commit=False)
            inv.vendor = vendor
            inv.save()
            return redirect(index)
    else:
        formulario = VendorInventoryForm()
    return render(request, 'catalog/crear_inventario.html', {
        'formulario': formulario,
        'vendor': vendor,
    })


def editar_inventario(request, id):
    inventario = VendorInventory.objects.get(id=id)
    if request.method == 'POST':
        formulario = VendorInventoryForm(request.POST, instance=inventario)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = VendorInventoryForm(instance=inventario)
    return render(request, 'catalog/editar_inventario.html', {
        'formulario': formulario,
        'inventario': inventario,
    })


def eliminar_inventario(request, id):
    VendorInventory.objects.get(id=id).delete()
    return redirect(index)
