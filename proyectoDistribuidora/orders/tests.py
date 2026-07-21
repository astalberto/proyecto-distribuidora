import threading
from decimal import Decimal

from django.db import OperationalError, connection
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from accounts.models import Distributor, Notification, Role, User
from catalog.models import Brand, Category, Product, StockLevel, UnitOfMeasure, Warehouse
from .forms import OrderItemForm
from .models import Order, OrderItem, OrderStatus


def make_distributor():
    return Distributor.objects.create(name='Distribuidora Test', email='dist@test.com')


def make_product(distributor, sku='SKU-1', price='10.00'):
    category = Category.objects.create(distributor=distributor, name='General')
    brand = Brand.objects.create(distributor=distributor, name='Marca')
    return Product.objects.create(
        distributor=distributor, name='Producto', sku=sku, category=category, brand=brand,
        unit_price=Decimal(price), unit_of_measure=UnitOfMeasure.PIECE,
    )


class OrderAcceptStockLevelTest(TestCase):
    """Tier 4.5 regression suite (docs/TODOS.md): StockLevel replaces
    VendorInventory as aceptar_pedido's lock target. These tests re-verify
    the Tier 2 concurrency-critical accept flow against the new model."""

    def setUp(self):
        self.distributor = make_distributor()
        self.vendor = User.objects.create_user(
            email='vendor@test.com', password='pass1234', role=Role.VENDOR, distributor=self.distributor
        )
        self.owner = User.objects.create_user(
            email='owner@test.com', password='pass1234', role=Role.STORE_OWNER, distributor=self.distributor
        )
        from catalog.models import Store
        self.store = Store.objects.create(
            name='Tienda', distributor=self.distributor, owner=self.owner, vendor=self.vendor
        )
        self.product = make_product(self.distributor)
        self.warehouse = Warehouse.objects.create(distributor=self.distributor, name='Principal')
        self.stock = StockLevel.objects.create(product=self.product, warehouse=self.warehouse, quantity=10)

        self.order = Order.objects.create(store=self.store, vendor=self.vendor, status=OrderStatus.PENDING)
        OrderItem.objects.create(
            order=self.order, product=self.product, warehouse=self.warehouse,
            quantity=4, unit_price_at_time=self.product.unit_price,
        )

    def _accept(self):
        client = Client()
        client.force_login(self.vendor)
        return client.post(reverse('aceptar_pedido', args=[self.order.id]))

    def test_accept_deducts_stock_and_transitions_to_accepted(self):
        self._accept()
        self.order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.ACCEPTED)
        self.assertEqual(self.stock.quantity, 6)

    def test_accept_notifies_store_owner(self):
        self._accept()
        self.assertTrue(
            Notification.objects.filter(user=self.owner, order=self.order).exists()
        )

    def test_insufficient_stock_rolls_back_order_stays_pending(self):
        self.stock.quantity = 2  # less than the 4 requested
        self.stock.save()
        self._accept()
        self.order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.PENDING)
        self.assertEqual(self.stock.quantity, 2)  # unchanged — nothing written

    def test_second_order_fails_after_first_depletes_stock(self):
        """Sequential double-spend regression: two orders against the same
        (product, warehouse) — the first accept must not let the second
        oversell what's left."""
        second_order = Order.objects.create(store=self.store, vendor=self.vendor, status=OrderStatus.PENDING)
        OrderItem.objects.create(
            order=second_order, product=self.product, warehouse=self.warehouse,
            quantity=8, unit_price_at_time=self.product.unit_price,
        )
        self._accept()  # first order takes 4, leaving 6
        client = Client()
        client.force_login(self.vendor)
        client.post(reverse('aceptar_pedido', args=[second_order.id]))
        second_order.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(second_order.status, OrderStatus.PENDING)  # 8 > 6 remaining — rejected
        self.assertEqual(self.stock.quantity, 6)  # only the first accept deducted


class OrderItemFormFR053Test(TestCase):
    """FR-05.3 resolution (Tier 4.5): any active product in the distributor's
    catalog is orderable, not scoped to what a specific vendor stocks."""

    def test_product_queryset_not_scoped_by_vendor(self):
        distributor = make_distributor()
        vendor = User.objects.create_user(
            email='v@test.com', password='pass1234', role=Role.VENDOR, distributor=distributor
        )
        product = make_product(distributor)  # not stocked by any specific vendor
        formulario = OrderItemForm(vendor=vendor)
        self.assertIn(product, formulario.fields['product'].queryset)

    def test_inactive_product_excluded(self):
        from catalog.models import ProductStatus
        distributor = make_distributor()
        vendor = User.objects.create_user(
            email='v2@test.com', password='pass1234', role=Role.VENDOR, distributor=distributor
        )
        product = make_product(distributor, sku='INACTIVE-1')
        product.status = ProductStatus.INACTIVE
        product.save()
        formulario = OrderItemForm(vendor=vendor)
        self.assertNotIn(product, formulario.fields['product'].queryset)


class OrderAcceptConcurrencyTest(TransactionTestCase):
    """Genuine multi-threaded regression for the select_for_update() lock.
    SQLite serializes writers at the database-file level (no true row-level
    concurrency), so this proves "no double-spend", not "both threads ran
    in true parallel" — the latter needs Postgres. A thread that hits
    OperationalError (database is locked) is treated as a losing thread,
    not a failure, since that's SQLite's own serialization mechanism."""

    def test_concurrent_accepts_exactly_one_succeeds(self):
        distributor = make_distributor()
        vendor = User.objects.create_user(
            email='cvendor@test.com', password='pass1234', role=Role.VENDOR, distributor=distributor
        )
        owner = User.objects.create_user(
            email='cowner@test.com', password='pass1234', role=Role.STORE_OWNER, distributor=distributor
        )
        from catalog.models import Store
        store = Store.objects.create(name='Tienda', distributor=distributor, owner=owner, vendor=vendor)
        product = make_product(distributor)
        warehouse = Warehouse.objects.create(distributor=distributor, name='Principal')
        StockLevel.objects.create(product=product, warehouse=warehouse, quantity=5)

        orders = []
        for _ in range(2):
            order = Order.objects.create(store=store, vendor=vendor, status=OrderStatus.PENDING)
            OrderItem.objects.create(
                order=order, product=product, warehouse=warehouse,
                quantity=5, unit_price_at_time=product.unit_price,
            )
            orders.append(order)

        def accept(order_id):
            try:
                client = Client()
                client.force_login(vendor)
                client.post(reverse('aceptar_pedido', args=[order_id]))
            except OperationalError:
                pass  # SQLite lock contention — treated as this thread losing
            finally:
                connection.close()

        threads = [threading.Thread(target=accept, args=(o.id,)) for o in orders]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for order in orders:
            order.refresh_from_db()
        accepted_count = sum(1 for o in orders if o.status == OrderStatus.ACCEPTED)
        self.assertEqual(accepted_count, 1)  # exactly one accept wins, never both
        stock = StockLevel.objects.get(product=product, warehouse=warehouse)
        self.assertEqual(stock.quantity, 0)  # only one deduction happened
