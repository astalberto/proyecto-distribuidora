Link del replit

https://isber-distribution-hub--josuexpardoch.replit.app/

## Cómo levantar el proyecto desde cero 

### 1. Entorno

**SQLite (por defecto):**
```
cd proyectoDistribuidora
python.exe manage.py migrate
```

### 2. Crear la primera cuenta (flujo DR-08)

```
../.venv/Scripts/python.exe manage.py createsuperuser
```
Ya logueado como ese superusuario en el navegador:

1. **`/accounts/distributors/new/`** (sin link en el nav, solo por URL directa) — crea la `Distributor` y su primer usuario `DISTRIBUTOR` juntos, en un solo formulario.
2. Cerrar sesión del superusuario, entrar como ese nuevo admin `DISTRIBUTOR`.
3. **`/accounts/users/`** — crear usuarios `VENDOR`/`DELIVERY` directo (botones en esa página); copiar el "enlace de registro para dueños de tienda" para que un `STORE_OWNER` se registre solo, o crearlo manualmente igual.
4. **`/catalog/`** — crear al menos un `Product`, luego asignarlo al vendedor en `/catalog/inventory/assign/<vendor_id>/` (el ID del vendedor sale de `/accounts/users/`).
5. **`/catalog/`** → crear una `Store`, con `owner` = el dueño de tienda y `vendor` = el vendedor (o saltarse esto si la tienda se autorregistra por el enlace — igual hay que asignarle vendedor después, por DR-01).

### 3. Probar el ciclo de vida de un pedido

1. Como **STORE_OWNER** → `/orders/new/` → agregar items → queda `PENDING`.
2. Como **VENDOR** → `/orders/` → aceptar (descuenta stock) → despachar.
3. Como **DELIVERY** → `/deliveries/new/confirm/` → elegir el pedido despachado → confirmar (pasa a `DELIVERED`).
4. De vuelta como **STORE_OWNER** → confirmar recepción (pasa a `CONFIRMED`) o reportar un problema (pasa a `DELIVERY_ISSUE`, y el `VENDOR` lo resuelve después).

---

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

DISTRIBUTOR (dueño de la distribuidora)
    Gestiona el catálogo de productos (crear/editar/desactivar-reactivar productos)
    Asigna inventario a cada vendedor (VendorInventory)
    Crea usuarios de las otras 3 categorías (páginas separadas por rol: Vendedor / Dueño de Tienda / Repartidor)
    Ve el dashboard de operaciones (pedidos por estado, niveles de stock)
    Consulta el AuditLog (historial de cambios)

    
VENDOR (vendedor)
    ⚠ Ver su propio inventario (UC-09) — todavía NO hay una pantalla para esto; el stock del vendedor solo se ve indirectamente en el mensaje de error si falla un "aceptar" por falta de stock
    Ve pedidos pendientes de las tiendas que le fueron asignadas (dashboard con polling cada 30s a /api/orders/pending/)
    Acepta un pedido → debe descontar inventario de forma atómica (transaction.atomic() + select_for_update())
    Rechaza un pedido → con motivo opcional
    Despacha un pedido aceptado → pasa a DISPATCHED y queda visible para repartidores

    
STORE_OWNER (dueño de tienda)
    Hace pedidos (Place Order) al vendedor asignado a su tienda (Store.vendor)
    Rastrea el estado de sus pedidos
    Recibe notificaciones in-app cuando cambia el estado
    ⚠ Reenviar un pedido rechazado (US-22) — el campo previous_order existe en el modelo pero todavía NO está implementado el botón/flujo
    Puede cancelar un pedido mientras esté PENDING
    Confirma la recepción de un pedido DELIVERED, o reporta un problema (DR-09)

    
DELIVERY (repartidor)
    Ve todos los pedidos DISPATCHED de su distribuidora (no hay asignación por ruta en el MVP — es "quien llega primero")
    Confirma la entrega —  → pasa el pedido a DELIVERED
    Máquina de estados del pedido:
    PENDING → ACCEPTED → DISPATCHED → DELIVERED → CONFIRMED (o DELIVERED → DELIVERY_ISSUE → CONFIRMED), o PENDING → REJECTED
