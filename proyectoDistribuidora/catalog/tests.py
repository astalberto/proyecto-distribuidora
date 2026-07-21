from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Distributor, Role, User
from .forms import ProductForm
from .models import (
    Brand,
    Category,
    Discount,
    DiscountType,
    Product,
    ProductStatus,
    StockLevel,
    UnitOfMeasure,
    Warehouse,
)


def make_distributor(name='Distribuidora Test'):
    return Distributor.objects.create(name=name, email=f'{name.lower().replace(" ", "")}@test.com')


def make_distributor_user(distributor, email='admin@test.com'):
    return User.objects.create_user(
        email=email, password='pass1234', role=Role.DISTRIBUTOR, distributor=distributor
    )


def make_product(distributor, sku='SKU-1', name='Producto', price='10.00'):
    category = Category.objects.create(distributor=distributor, name='General')
    brand = Brand.objects.create(distributor=distributor, name='Marca')
    return Product.objects.create(
        distributor=distributor,
        name=name,
        sku=sku,
        category=category,
        brand=brand,
        unit_price=Decimal(price),
        unit_of_measure=UnitOfMeasure.PIECE,
    )


class ProductSkuUniquenessTest(TestCase):
    def test_same_sku_different_distributors_allowed(self):
        d1 = make_distributor('D1')
        d2 = make_distributor('D2')
        make_product(d1, sku='ABC')
        # Should NOT raise — SKU uniqueness is per-distributor, not global.
        make_product(d2, sku='ABC')
        self.assertEqual(Product.objects.filter(sku='ABC').count(), 2)

    def test_same_sku_same_distributor_rejected(self):
        d1 = make_distributor('D1')
        make_product(d1, sku='ABC')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_product(d1, sku='ABC', name='Otro producto')


class DiscountCurrentPriceTest(TestCase):
    def setUp(self):
        self.distributor = make_distributor()
        self.product = make_product(self.distributor, price='100.00')

    def test_no_discount_returns_unit_price(self):
        self.assertEqual(self.product.current_price(), Decimal('100.00'))

    def test_percentage_discount_active(self):
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal('15'),
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
        )
        self.assertEqual(self.product.current_price(), Decimal('85.00'))

    def test_fixed_amount_discount_active(self):
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal('30.00'),
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
        )
        self.assertEqual(self.product.current_price(), Decimal('70.00'))

    def test_discount_clamped_at_zero(self):
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal('500.00'),
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
        )
        self.assertEqual(self.product.current_price(), 0)

    def test_expired_discount_reverts_to_unit_price(self):
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal('50'),
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=1),
        )
        self.assertEqual(self.product.current_price(), Decimal('100.00'))

    def test_overlapping_discounts_rejected(self):
        Discount.objects.create(
            product=self.product,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal('10'),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
        )
        overlapping = Discount(
            product=self.product,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal('20'),
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=15),
        )
        with self.assertRaises(ValidationError):
            overlapping.clean()


class StockDerivationTest(TestCase):
    def setUp(self):
        self.distributor = make_distributor()
        self.product = make_product(self.distributor)
        self.warehouse = Warehouse.objects.create(distributor=self.distributor, name='Principal')

    def test_out_of_stock_when_no_stock_level_rows(self):
        self.assertTrue(self.product.is_out_of_stock())
        self.assertEqual(self.product.total_stock(), 0)

    def test_out_of_stock_when_quantity_zero(self):
        StockLevel.objects.create(product=self.product, warehouse=self.warehouse, quantity=0)
        self.assertTrue(self.product.is_out_of_stock())

    def test_in_stock_when_quantity_positive(self):
        StockLevel.objects.create(product=self.product, warehouse=self.warehouse, quantity=5)
        self.assertFalse(self.product.is_out_of_stock())
        self.assertEqual(self.product.total_stock(), 5)


class ProductFormTenantScopingTest(TestCase):
    def test_category_and_brand_scoped_to_distributor(self):
        d1 = make_distributor('D1')
        d2 = make_distributor('D2')
        cat1 = Category.objects.create(distributor=d1, name='Cat1')
        Category.objects.create(distributor=d2, name='Cat2')

        formulario = ProductForm(distributor=d1)
        self.assertIn(cat1, formulario.fields['category'].queryset)
        self.assertEqual(formulario.fields['category'].queryset.count(), 1)


class CategoryTenantIsolationViewTest(TestCase):
    def setUp(self):
        self.d1 = make_distributor('D1')
        self.d2 = make_distributor('D2')
        self.user1 = make_distributor_user(self.d1, 'u1@test.com')
        Category.objects.create(distributor=self.d1, name='CatD1')
        Category.objects.create(distributor=self.d2, name='CatD2')

    def test_catalog_index_only_shows_own_distributor_categories(self):
        client = Client()
        client.force_login(self.user1)
        response = client.get(reverse('index_catalog'))
        self.assertContains(response, 'CatD1')
        self.assertNotContains(response, 'CatD2')


class ProductViewsSmokeTest(TestCase):
    """Every new/extended view actually renders for a logged-in distributor.
    Catches URL/view kwarg-name mismatches that model- and form-level tests
    above don't exercise (e.g. gestionar_descuento/editar_stock originally
    declared as <int:id> in urls.py but product_id in the view signature)."""

    def setUp(self):
        self.distributor = make_distributor()
        self.user = make_distributor_user(self.distributor)
        self.product = make_product(self.distributor)
        self.client = Client()
        self.client.force_login(self.user)

    def test_all_product_related_views_return_200(self):
        paths = [
            reverse('index_catalog'),
            reverse('crear_producto'),
            reverse('editar_producto', args=[self.product.id]),
            reverse('gestionar_descuento', args=[self.product.id]),
            reverse('editar_stock', args=[self.product.id]),
            reverse('importar_productos'),
            reverse('crear_categoria'),
            reverse('crear_marca'),
        ]
        for path in paths:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, f'{path} returned {response.status_code}')

    def test_editar_stock_updates_quantity_and_triggers_digest_check(self):
        warehouse = Warehouse.get_or_create_default(self.distributor)
        response = self.client.post(
            reverse('editar_stock', args=[self.product.id]), {'quantity': '7'}
        )
        self.assertEqual(response.status_code, 302)
        stock = StockLevel.objects.get(product=self.product, warehouse=warehouse)
        self.assertEqual(stock.quantity, 7)


class CsvImportTest(TestCase):
    def setUp(self):
        self.distributor = make_distributor()
        self.user = make_distributor_user(self.distributor)
        self.category = Category.objects.create(distributor=self.distributor, name='Bebidas')
        self.brand = Brand.objects.create(distributor=self.distributor, name='CocaCola')
        Product.objects.create(
            distributor=self.distributor, name='Existente', sku='DUP',
            category=self.category, brand=self.brand, unit_price=Decimal('1.00'),
        )

    def _csv_file(self, content):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile('import.csv', content.encode('utf-8'), content_type='text/csv')

    def test_row_level_skip_valid_and_invalid_rows(self):
        csv_content = (
            'nombre,sku,codigo_barras,categoria,brand,precio,unidad_medida,stock_minimo\n'
            'Producto Valido,NEW1,123,Bebidas,CocaCola,5.50,PIECE,5\n'
            'Producto Duplicado,DUP,124,Bebidas,CocaCola,5.50,PIECE,5\n'
            'Producto Sin Categoria,NEW2,125,NoExiste,CocaCola,5.50,PIECE,5\n'
        )
        client = Client()
        client.force_login(self.user)
        response = client.post(
            reverse('importar_productos'),
            {'archivo_csv': self._csv_file(csv_content)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 producto(s) importado')
        self.assertContains(response, 'SKU')
        self.assertTrue(Product.objects.filter(sku='NEW1').exists())
        self.assertFalse(Product.objects.filter(sku='NEW2').exists())
        # The pre-existing DUP row must be untouched, not overwritten.
        self.assertEqual(Product.objects.filter(sku='DUP').count(), 1)

    def test_formula_injection_sanitized(self):
        csv_content = (
            'nombre,sku,codigo_barras,categoria,brand,precio,unidad_medida,stock_minimo\n'
            '=cmd(),NEW3,123,Bebidas,CocaCola,5.50,PIECE,5\n'
        )
        client = Client()
        client.force_login(self.user)
        client.post(reverse('importar_productos'), {'archivo_csv': self._csv_file(csv_content)})
        producto = Product.objects.get(sku='NEW3')
        self.assertFalse(producto.name.startswith('='))
