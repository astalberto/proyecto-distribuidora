from django.shortcuts import get_object_or_404, render, redirect

from accounts.decorators import role_required
from accounts.models import User
from .models import Store, Product, VendorInventory
from .forms import StoreForm, ProductForm, VendorInventoryForm


@role_required('DISTRIBUTOR')
def index(request):
    distribuidor = request.user.distributor
    return render(request, 'catalog/index.html', {
        # NFR-02.5: catalog/index.html displays distributor/owner/vendor
        # (Store), distributor (Product), and vendor/product (VendorInventory)
        # per row — eager-load to avoid an N+1 per row.
        'tiendas': Store.objects.filter(distributor=distribuidor)
            .select_related('distributor', 'owner', 'vendor'),
        'productos': Product.objects.filter(distributor=distribuidor)  # active + inactive
            .select_related('distributor'),
        'inventarios': VendorInventory.objects.filter(vendor__distributor=distribuidor)
            .select_related('vendor', 'product'),
    })


# --- Store ---

@role_required('DISTRIBUTOR')
def crear_tienda(request):
    if request.method == 'POST':
        formulario = StoreForm(request.POST, distributor=request.user.distributor)
        if formulario.is_valid():
            tienda = formulario.save(commit=False)
            tienda.distributor = request.user.distributor
            tienda.save()
            return redirect(index)
    else:
        formulario = StoreForm(distributor=request.user.distributor)
    return render(request, 'catalog/crear_tienda.html', {'formulario': formulario})


@role_required('DISTRIBUTOR')
def editar_tienda(request, id):
    tienda = get_object_or_404(Store, id=id, distributor=request.user.distributor)
    if request.method == 'POST':
        formulario = StoreForm(request.POST, instance=tienda, distributor=request.user.distributor)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = StoreForm(instance=tienda, distributor=request.user.distributor)
    return render(request, 'catalog/editar_tienda.html', {
        'formulario': formulario,
        'tienda': tienda,
    })


@role_required('DISTRIBUTOR')
def eliminar_tienda(request, id):
    get_object_or_404(Store, id=id, distributor=request.user.distributor).delete()
    return redirect(index)


# --- Product ---

@role_required('DISTRIBUTOR')
def crear_producto(request):
    if request.method == 'POST':
        formulario = ProductForm(request.POST)
        if formulario.is_valid():
            producto = formulario.save(commit=False)
            producto.distributor = request.user.distributor
            producto.save()
            return redirect(index)
    else:
        formulario = ProductForm()
    return render(request, 'catalog/crear_producto.html', {'formulario': formulario})


@role_required('DISTRIBUTOR')
def editar_producto(request, id):
    producto = get_object_or_404(Product, id=id, distributor=request.user.distributor)
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


@role_required('DISTRIBUTOR')
def eliminar_producto(request, id):
    # DR-06: soft-delete only — hard delete would cascade to OrderItems
    producto = get_object_or_404(Product, id=id, distributor=request.user.distributor)
    producto.is_active = False
    producto.save(update_fields=['is_active'])
    return redirect(index)


@role_required('DISTRIBUTOR')
def reactivar_producto(request, id):
    producto = get_object_or_404(Product, id=id, distributor=request.user.distributor)
    producto.is_active = True
    producto.save(update_fields=['is_active'])
    return redirect(index)


# --- VendorInventory — vendor injected via URL ---

@role_required('DISTRIBUTOR')
def crear_inventario(request, vendor_id):
    vendor = get_object_or_404(User, id=vendor_id, distributor=request.user.distributor, role='VENDOR')
    if request.method == 'POST':
        formulario = VendorInventoryForm(request.POST, distributor=request.user.distributor)
        if formulario.is_valid():
            inv = formulario.save(commit=False)
            inv.vendor = vendor
            inv.save()
            return redirect(index)
    else:
        formulario = VendorInventoryForm(distributor=request.user.distributor)
    return render(request, 'catalog/crear_inventario.html', {
        'formulario': formulario,
        'vendor': vendor,
    })


@role_required('DISTRIBUTOR')
def editar_inventario(request, id):
    inventario = get_object_or_404(VendorInventory, id=id, vendor__distributor=request.user.distributor)
    if request.method == 'POST':
        formulario = VendorInventoryForm(request.POST, instance=inventario, distributor=request.user.distributor)
        if formulario.is_valid():
            formulario.save()
            return redirect(index)
    else:
        formulario = VendorInventoryForm(instance=inventario, distributor=request.user.distributor)
    return render(request, 'catalog/editar_inventario.html', {
        'formulario': formulario,
        'inventario': inventario,
    })


@role_required('DISTRIBUTOR')
def eliminar_inventario(request, id):
    get_object_or_404(VendorInventory, id=id, vendor__distributor=request.user.distributor).delete()
    return redirect(index)
