from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from rest_framework.authtoken.views import obtain_auth_token

from orders.views import pending_orders_api

urlpatterns = [
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('admin/', admin.site.urls),

    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('accounts/', include('accounts.urls')),
    path('catalog/', include('catalog.urls')),
    path('orders/', include('orders.urls')),
    path('deliveries/', include('deliveries.urls')),
    path('audit/', include('audit.urls')),

    # Vendor dashboard 30s polling target (FR-06.6, FR-10.1) — distinct from
    # the general-purpose catalog REST API below.
    path('api/orders/pending/', pending_orders_api, name='api_orders_pending'),

    path('api/', include('catalog.api_urls')),
    path('api/token-auth/', obtain_auth_token, name='api_token_auth'),
    path('api-auth/', include('rest_framework.urls')),
]