from rest_framework import viewsets

from .models import Store, Product, VendorInventory
from .serializers import StoreSerializer, ProductSerializer, VendorInventorySerializer


class StoreViewSet(viewsets.ModelViewSet):
    """
    API REST para Tiendas (Store).
    Requiere autenticación por token (o sesión). Ver /api/token-auth/.
    """
    queryset = Store.objects.all()
    serializer_class = StoreSerializer


class ProductViewSet(viewsets.ModelViewSet):
    """
    API REST para Productos (Product).
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class VendorInventoryViewSet(viewsets.ModelViewSet):
    """
    API REST para Inventario por Vendedor (VendorInventory).
    """
    queryset = VendorInventory.objects.all()
    serializer_class = VendorInventorySerializer
