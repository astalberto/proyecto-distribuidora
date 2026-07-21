from rest_framework.routers import DefaultRouter

from .api_views import StoreViewSet, ProductViewSet, VendorInventoryViewSet

router = DefaultRouter()
router.register(r'stores', StoreViewSet, basename='api-store')
router.register(r'products', ProductViewSet, basename='api-product')
router.register(r'inventory', VendorInventoryViewSet, basename='api-inventory')

urlpatterns = router.urls
