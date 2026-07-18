Link del replit

https://isber-distribution-hub--josuexpardoch.replit.app/



http://127.0.0.1:8000/accounts/ 
Admnistrador: admin@isber.ec password123 testpass123 

Vendedor: vendedor@isber.ec password123 testpass123 

Tienda: tienda@isber.ec password123 testpass123 

Repartidor: repartidor@isber.ec password123 testpass123 


<img width="657" height="321" alt="image" src="https://github.com/user-attachments/assets/d93822dd-51cc-4757-b0e8-cbce0d48f730" />



http://127.0.0.1:8000/catalog/ 
http://127.0.0.1:8000/orders/ 
http://127.0.0.1:8000/deliveries/ 
http://127.0.0.1:8000/audit/

http://127.0.0.1:8000/ (home)   
http://127.0.0.1:8000/login/
http://127.0.0.1:8000/logout/

API (Django REST Framework):

http://127.0.0.1:8000/api/stores/
http://127.0.0.1:8000/api/products/
http://127.0.0.1:8000/api/inventory/
http://127.0.0.1:8000/api/token-auth/ (obtener token de autenticación)
http://127.0.0.1:8000/api-auth/ (login/logout de la API navegable de DRF)


Los 4 roles del sistema
Según docs/requirements.md, el sistema tiene 4 roles fijos (Distributor/User.role en proyectoDistribuidora/accounts/models.py):

🏭 DISTRIBUTOR (dueño de la distribuidora)
    Gestiona el catálogo de productos (crear/editar/desactivar-reactivar productos)
    Asigna inventario a cada vendedor (VendorInventory)
    Crea usuarios de las otras 3 categorías (páginas separadas por rol: Vendedor / Dueño de Tienda / Repartidor)
    Ve el dashboard de operaciones (pedidos por estado, niveles de stock)
    Consulta el AuditLog (historial de cambios)
🚚 VENDOR (vendedor)
    Ve su inventario asignado
    Ve pedidos pendientes de las tiendas que le fueron asignadas (dashboard con polling cada 30s a /api/orders/pending/)
    Acepta un pedido → debe descontar inventario de forma atómica (transaction.atomic() + select_for_update())
    Rechaza un pedido → con motivo opcional
    Despacha un pedido aceptado → pasa a DISPATCHED y queda visible para repartidores
🏪 STORE_OWNER (dueño de tienda)
    Hace pedidos (Place Order) al vendedor asignado a su tienda (Store.vendor)
    Rastrea el estado de sus pedidos
    Recibe notificaciones in-app cuando cambia el estado
    Puede reenviar un pedido rechazado (crea un nuevo Order con previous_order apuntando al rechazado)
    Puede cancelar un pedido mientras esté PENDING
📦 DELIVERY (repartidor)
    Ve todos los pedidos DISPATCHED de su distribuidora (no hay asignación por ruta en el MVP — es "quien llega primero")
    Confirma la entrega subiendo una foto (va directo a Cloudinary, el servidor valida el public_id) → pasa el pedido a DELIVERED
    Máquina de estados del pedido:
    PENDING → ACCEPTED → DISPATCHED → DELIVERED, o PENDING → REJECTED (con posible reenvío como nuevo pedido).