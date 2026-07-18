from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from .models import Store, Product, VendorInventory
from .serializers import StoreSerializer, ProductSerializer, VendorInventorySerializer
from .permissions import IsDistributor


class StoreViewSet(viewsets.ModelViewSet):
    """
    API REST para Tiendas (Store).
    Requiere autenticación (token o sesión, ver /api/token-auth/) y rol
    DISTRIBUTOR. Todas las operaciones quedan acotadas al distribuidor
    del usuario autenticado.
    """
    serializer_class = StoreSerializer
    permission_classes = [IsDistributor]

    def get_queryset(self):
        return Store.objects.filter(distributor=self.request.user.distributor)

    def perform_create(self, serializer):
        owner = serializer.validated_data.get('owner')
        vendor = serializer.validated_data.get('vendor')
        distributor = self.request.user.distributor
        if owner is not None and owner.distributor_id != distributor.id:
            raise PermissionDenied('owner debe pertenecer al mismo distribuidor.')
        if vendor is not None and vendor.distributor_id != distributor.id:
            raise PermissionDenied('vendor debe pertenecer al mismo distribuidor.')
        serializer.save(distributor=distributor)


class ProductViewSet(viewsets.ModelViewSet):
    """
    API REST para Productos (Product).
    Acotada al distribuidor del usuario autenticado.
    """
    serializer_class = ProductSerializer
    permission_classes = [IsDistributor]

    def get_queryset(self):
        return Product.objects.filter(distributor=self.request.user.distributor)

    def perform_create(self, serializer):
        serializer.save(distributor=self.request.user.distributor)


class VendorInventoryViewSet(viewsets.ModelViewSet):
    """
    API REST para Inventario por Vendedor (VendorInventory).
    Acotada al distribuidor del usuario autenticado a través de vendor.
    """
    serializer_class = VendorInventorySerializer
    permission_classes = [IsDistributor]

    def get_queryset(self):
        return VendorInventory.objects.filter(vendor__distributor=self.request.user.distributor)

    def perform_create(self, serializer):
        distributor = self.request.user.distributor
        vendor = serializer.validated_data.get('vendor')
        product = serializer.validated_data.get('product')
        if vendor is not None and vendor.distributor_id != distributor.id:
            raise PermissionDenied('vendor debe pertenecer al mismo distribuidor.')
        if product is not None and product.distributor_id != distributor.id:
            raise PermissionDenied('product debe pertenecer al mismo distribuidor.')
        serializer.save()
