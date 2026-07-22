import csv
import io

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, render, redirect

from accounts.decorators import role_required
from accounts.models import Notification, Role, User
from audit.models import AuditLog
from .models import (
    Brand,
    Category,
    Discount,
    Product,
    ProductImage,
    ProductStatus,
    StockLevel,
    Store,
    UnitOfMeasure,
    Warehouse,
)
from .forms import (
    BrandForm,
    CategoryForm,
    DiscountForm,
    ProductForm,
    ProductImportForm,
    StoreForm,
)


def check_low_stock_digest(distributor, actor):
    """Bundled low-stock digest (Tier 4.5, accepted in /plan-ceo-review):
    one Notification per DISTRIBUTOR user summarizing every product
    currently crossing low_stock_threshold, instead of one notification
    per product. Checked on every product/stock save (synchronous,
    request-response — no background job infra in this app)."""
    productos = Product.objects.filter(
        distributor=distributor, status=ProductStatus.ACTIVE
    ).prefetch_related('stock_levels')
    bajos = [p for p in productos if p.total_stock() < p.low_stock_threshold]
    if not bajos:
        return
    nombres = ', '.join(p.name for p in bajos[:10])
    if len(bajos) > 10:
        nombres += f' y {len(bajos) - 10} más'
    mensaje = f'⚠ {len(bajos)} producto(s) con stock bajo: {nombres}'
    for user in User.objects.filter(distributor=distributor, role=Role.DISTRIBUTOR):
        Notification.objects.create(user=user, order=None, message=mensaje)


@role_required('DISTRIBUTOR')
def index(request):
    return render(request, 'catalog/index.html')


@role_required('DISTRIBUTOR')
def index_productos(request):
    distribuidor = request.user.distributor

    productos = (
        Product.objects.filter(distributor=distribuidor)
        .select_related('category', 'brand')
        .prefetch_related('stock_levels', 'discounts')
    )

    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    brand_id = request.GET.get('brand', '')
    stock_status = request.GET.get('stock_status', '')
    only_on_sale = request.GET.get('only_on_sale', '')

    if q:
        from django.db.models import Q
        productos = productos.filter(
            Q(name__icontains=q) | Q(sku__icontains=q) | Q(barcode__icontains=q)
        )
    if category_id:
        productos = productos.filter(category_id=category_id)
    if brand_id:
        productos = productos.filter(brand_id=brand_id)

    productos = list(productos)
    if stock_status == 'in_stock':
        productos = [p for p in productos if p.total_stock() > 0]
    elif stock_status == 'low':
        productos = [p for p in productos if 0 < p.total_stock() < p.low_stock_threshold]
    elif stock_status == 'out':
        productos = [p for p in productos if p.total_stock() == 0]
    if only_on_sale:
        productos = [p for p in productos if p.active_discount() is not None]

    return render(request, 'catalog/index_productos.html', {
        'productos': productos,
        'categorias': Category.objects.filter(distributor=distribuidor),
        'marcas': Brand.objects.filter(distributor=distribuidor),
        'filtros': {
            'q': q, 'category': category_id, 'brand': brand_id,
            'stock_status': stock_status, 'only_on_sale': only_on_sale,
        },
    })


@role_required('DISTRIBUTOR')
def index_categorias(request):
    categorias = Category.objects.filter(distributor=request.user.distributor)
    return render(request, 'catalog/index_categorias.html', {'categorias': categorias})


@role_required('DISTRIBUTOR')
def index_marcas(request):
    marcas = Brand.objects.filter(distributor=request.user.distributor)
    return render(request, 'catalog/index_marcas.html', {'marcas': marcas})


# --- Store ---

@role_required('DISTRIBUTOR')
def crear_tienda(request):
    if request.method == 'POST':
        formulario = StoreForm(request.POST, distributor=request.user.distributor)
        if formulario.is_valid():
            tienda = formulario.save(commit=False)
            tienda.distributor = request.user.distributor
            tienda.save()
            return redirect('index_accounts')
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
            return redirect('index_accounts')
    else:
        formulario = StoreForm(instance=tienda, distributor=request.user.distributor)
    return render(request, 'catalog/editar_tienda.html', {
        'formulario': formulario,
        'tienda': tienda,
    })


@role_required('DISTRIBUTOR')
def eliminar_tienda(request, id):
    get_object_or_404(Store, id=id, distributor=request.user.distributor).delete()
    return redirect('index_accounts')


# --- Category ---

@role_required('DISTRIBUTOR')
def crear_categoria(request):
    is_popup = 'popup' in request.GET or 'popup' in request.POST
    if request.method == 'POST':
        formulario = CategoryForm(request.POST)
        if formulario.is_valid():
            categoria = formulario.save(commit=False)
            categoria.distributor = request.user.distributor
            categoria.save()
            if is_popup:
                return render(request, 'catalog/popup_creado.html', {
                    'obj_id': categoria.id,
                    'obj_name': categoria.name,
                    'callback': 'refreshCategorySelect',
                })
            return redirect('index_categorias')
    else:
        formulario = CategoryForm()
    template = 'catalog/crear_categoria_popup.html' if is_popup else 'catalog/crear_categoria.html'
    return render(request, template, {'formulario': formulario})


@role_required('DISTRIBUTOR')
def editar_categoria(request, id):
    categoria = get_object_or_404(Category, id=id, distributor=request.user.distributor)
    if request.method == 'POST':
        formulario = CategoryForm(request.POST, instance=categoria)
        if formulario.is_valid():
            formulario.save()
            return redirect('index_categorias')
    else:
        formulario = CategoryForm(instance=categoria)
    return render(request, 'catalog/editar_categoria.html', {
        'formulario': formulario, 'categoria': categoria,
    })


# --- Brand ---

@role_required('DISTRIBUTOR')
def crear_marca(request):
    is_popup = 'popup' in request.GET or 'popup' in request.POST
    if request.method == 'POST':
        formulario = BrandForm(request.POST)
        if formulario.is_valid():
            marca = formulario.save(commit=False)
            marca.distributor = request.user.distributor
            marca.save()
            if is_popup:
                return render(request, 'catalog/popup_creado.html', {
                    'obj_id': marca.id,
                    'obj_name': marca.name,
                    'callback': 'refreshBrandSelect',
                })
            return redirect('index_marcas')
    else:
        formulario = BrandForm()
    template = 'catalog/crear_marca_popup.html' if is_popup else 'catalog/crear_marca.html'
    return render(request, template, {'formulario': formulario})


@role_required('DISTRIBUTOR')
def editar_marca(request, id):
    marca = get_object_or_404(Brand, id=id, distributor=request.user.distributor)
    if request.method == 'POST':
        formulario = BrandForm(request.POST, instance=marca)
        if formulario.is_valid():
            formulario.save()
            return redirect('index_marcas')
    else:
        formulario = BrandForm(instance=marca)
    return render(request, 'catalog/editar_marca.html', {
        'formulario': formulario, 'marca': marca,
    })


# --- Product ---

def _save_product_images(producto, formulario, request):
    main_image = formulario.cleaned_data.get('main_image')
    if main_image:
        ProductImage.objects.filter(product=producto, is_main=True).delete()
        ProductImage.objects.create(product=producto, image=main_image, is_main=True)
    for f in request.FILES.getlist('additional_images'):
        ProductImage.objects.create(product=producto, image=f, is_main=False)



@role_required('DISTRIBUTOR')
def crear_producto(request):
    distribuidor = request.user.distributor
    if request.method == 'POST':
        formulario = ProductForm(request.POST, request.FILES, distributor=distribuidor)
        if formulario.is_valid():
            producto = formulario.save(commit=False)
            producto.distributor = distribuidor
            producto.save()
            _save_product_images(producto, formulario, request)
            AuditLog.objects.create(
                user=request.user,
                action='product_created',
                entity_type='Product',
                entity_id=str(producto.id),
                details={'name': producto.name, 'sku': producto.sku},
            )
            check_low_stock_digest(distribuidor, request.user)
            return redirect('index_productos')
    else:
        formulario = ProductForm(distributor=distribuidor)
    return render(request, 'catalog/crear_producto.html', {'formulario': formulario})


@role_required('DISTRIBUTOR')
def editar_producto(request, id):
    distribuidor = request.user.distributor
    producto = get_object_or_404(Product, id=id, distributor=distribuidor)
    if request.method == 'POST':
        formulario = ProductForm(
            request.POST, request.FILES, instance=producto, distributor=distribuidor
        )
        if formulario.is_valid():
            formulario.save()
            _save_product_images(producto, formulario, request)
            AuditLog.objects.create(
                user=request.user,
                action='product_updated',
                entity_type='Product',
                entity_id=str(producto.id),
                details={'name': producto.name, 'sku': producto.sku},
            )
            check_low_stock_digest(distribuidor, request.user)
            return redirect('index_productos')
    else:
        formulario = ProductForm(instance=producto, distributor=distribuidor)
    return render(request, 'catalog/editar_producto.html', {
        'formulario': formulario,
        'producto': producto,
    })


@role_required('DISTRIBUTOR')
def eliminar_producto(request, id):
    # DR-06 (Tier 4.5): status -> INACTIVE, not a hard delete — hard delete
    # would cascade to OrderItems.
    producto = get_object_or_404(Product, id=id, distributor=request.user.distributor)
    producto.status = ProductStatus.INACTIVE
    producto.save(update_fields=['status'])
    AuditLog.objects.create(
        user=request.user,
        action='product_deactivated',
        entity_type='Product',
        entity_id=str(producto.id),
        details={'name': producto.name},
    )
    return redirect('index_productos')


@role_required('DISTRIBUTOR')
def reactivar_producto(request, id):
    producto = get_object_or_404(Product, id=id, distributor=request.user.distributor)
    producto.status = ProductStatus.ACTIVE
    producto.save(update_fields=['status'])
    AuditLog.objects.create(
        user=request.user,
        action='product_reactivated',
        entity_type='Product',
        entity_id=str(producto.id),
        details={'name': producto.name},
    )
    return redirect('index_productos')


@role_required('DISTRIBUTOR')
def descontinuar_producto(request, id):
    """Discontinued is a distinct explicit action from deactivate — never
    auto-mapped from is_active (Tier 4.5 resolution)."""
    producto = get_object_or_404(Product, id=id, distributor=request.user.distributor)
    producto.status = ProductStatus.DISCONTINUED
    producto.save(update_fields=['status'])
    AuditLog.objects.create(
        user=request.user,
        action='product_discontinued',
        entity_type='Product',
        entity_id=str(producto.id),
        details={'name': producto.name},
    )
    return redirect('index_productos')


# --- Discount ---

@role_required('DISTRIBUTOR')
def gestionar_descuento(request, product_id):
    producto = get_object_or_404(Product, id=product_id, distributor=request.user.distributor)
    descuento = producto.active_discount() or Discount.objects.filter(product=producto).order_by('-end_date').first()
    if request.method == 'POST':
        instance = descuento if descuento and descuento.pk else None
        formulario = DiscountForm(request.POST, instance=instance)
        if formulario.is_valid():
            nuevo = formulario.save(commit=False)
            nuevo.product = producto
            nuevo.full_clean()
            nuevo.save()
            return redirect('editar_producto', id=producto.id)
    else:
        formulario = DiscountForm(instance=descuento)
    return render(request, 'catalog/gestionar_descuento.html', {
        'formulario': formulario,
        'producto': producto,
    })


@role_required('DISTRIBUTOR')
def quitar_descuento(request, product_id):
    producto = get_object_or_404(Product, id=product_id, distributor=request.user.distributor)
    if request.method == 'POST':
        Discount.objects.filter(product=producto).delete()
    return redirect('editar_producto', id=producto.id)


# --- Stock (replaces the old per-vendor VendorInventory assignment) ---

@role_required('DISTRIBUTOR')
def editar_stock(request, product_id):
    producto = get_object_or_404(Product, id=product_id, distributor=request.user.distributor)
    warehouse = Warehouse.get_or_create_default(request.user.distributor)
    stock, _ = StockLevel.objects.get_or_create(product=producto, warehouse=warehouse)
    if request.method == 'POST':
        try:
            cantidad = int(request.POST.get('quantity', ''))
            if cantidad < 0:
                raise ValueError
        except (TypeError, ValueError):
            return render(request, 'catalog/editar_stock.html', {
                'producto': producto, 'stock': stock,
                'error': 'La cantidad debe ser un número entero no negativo.',
            })
        stock.quantity = cantidad
        stock.save(update_fields=['quantity'])
        check_low_stock_digest(request.user.distributor, request.user)
        return redirect('index_productos')
    return render(request, 'catalog/editar_stock.html', {'producto': producto, 'stock': stock})


# --- CSV Import ---

def _sanitize_cell(value):
    """Formula-injection guardrail (CEO review, Section 3): strip a leading
    =/+/-/@ so a value like "=cmd()" can't execute if this data is later
    opened in a spreadsheet."""
    value = (value or '').strip()
    if value and value[0] in ('=', '+', '-', '@'):
        return "'" + value
    return value


@role_required('DISTRIBUTOR')
def importar_productos(request):
    if request.method == 'POST':
        formulario = ProductImportForm(request.POST, request.FILES)
        if formulario.is_valid():
            distribuidor = request.user.distributor
            archivo = formulario.cleaned_data['archivo_csv']
            texto = archivo.read().decode('utf-8-sig', errors='replace')
            lector = csv.DictReader(io.StringIO(texto))

            importados = 0
            errores = []
            for numero, fila in enumerate(lector, start=2):  # header is row 1
                fila = {k: _sanitize_cell(v) for k, v in fila.items()}
                try:
                    with transaction.atomic():
                        categoria = Category.objects.get(
                            distributor=distribuidor, name=fila.get('categoria', '')
                        )
                        marca = Brand.objects.get(
                            distributor=distribuidor, name=fila.get('brand', '')
                        )
                        Product.objects.create(
                            distributor=distribuidor,
                            name=fila['nombre'],
                            sku=fila['sku'],
                            barcode=fila.get('codigo_barras', ''),
                            category=categoria,
                            brand=marca,
                            unit_price=fila['precio'],
                            unit_of_measure=fila.get('unidad_medida') or UnitOfMeasure.PIECE,
                            low_stock_threshold=fila.get('stock_minimo') or 5,
                        )
                        importados += 1
                except IntegrityError:
                    errores.append(f'Fila {numero}: SKU "{fila.get("sku", "")}" ya existe')
                except Category.DoesNotExist:
                    errores.append(f'Fila {numero}: categoría "{fila.get("categoria", "")}" no encontrada')
                except Brand.DoesNotExist:
                    errores.append(f'Fila {numero}: marca "{fila.get("brand", "")}" no encontrada')
                except (KeyError, ValueError):
                    errores.append(f'Fila {numero}: datos inválidos')

            if importados:
                AuditLog.objects.create(
                    user=request.user,
                    action='product_csv_import',
                    entity_type='Product',
                    entity_id='',
                    details={'imported': importados, 'errors': len(errores)},
                )
                check_low_stock_digest(distribuidor, request.user)
            return render(request, 'catalog/importar_productos_resultado.html', {
                'importados': importados, 'errores': errores,
            })
    else:
        formulario = ProductImportForm()
    return render(request, 'catalog/importar_productos.html', {'formulario': formulario})


@role_required('DISTRIBUTOR')
def mapa_tiendas(request):
    import json
    distribuidor = request.user.distributor
    tiendas = Store.objects.filter(distributor=distribuidor)
    markers = [
        {
            'id': t.id,
            'name': t.name,
            'address': t.address,
            'lat': float(t.latitude),
            'lng': float(t.longitude),
        }
        for t in tiendas
        if t.latitude is not None and t.longitude is not None
    ]
    sin_coords = [t for t in tiendas if t.latitude is None or t.longitude is None]
    return render(request, 'catalog/mapa_tiendas.html', {
        'markers_json': json.dumps(markers),
        'sin_coords': sin_coords,
        'distribuidor': distribuidor,
    })
