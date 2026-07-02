# UX Navigation Flows & Conceptual Wireframes
# ISBER Solutions Distribution Platform

**Author:** UX/Product Design  
**Based on:** `docs/requirements.md`  
**Last updated:** 2026-07-01  
**Roles in scope:** DISTRIBUTOR · VENDOR · STORE_OWNER · DELIVERY

---

## Table of Contents

1. [Global Entry Points & Shared Flows](#1-global-entry-points--shared-flows)
2. [DISTRIBUTOR Flows](#2-distributor-flows)
3. [VENDOR Flows](#3-vendor-flows)
4. [STORE_OWNER Flows](#4-store_owner-flows)
5. [DELIVERY Flows](#5-delivery-flows)
6. [Conceptual Wireframes](#6-conceptual-wireframes)

---

## 1. Global Entry Points & Shared Flows

### 1.1 Login Flow (UC-01 · US-01 · FR-01.1, FR-01.2)

```
[/] Root URL
  └─► Redirect → [/accounts/login/]

[Screen: Login]
  ├─► Valid credentials
  │     └─► POST /accounts/login/
  │           ├─► role = DISTRIBUTOR  → [/catalog/dashboard/]
  │           ├─► role = VENDOR       → [/orders/vendor-dashboard/]
  │           ├─► role = STORE_OWNER  → [/orders/store-dashboard/]
  │           └─► role = DELIVERY     → [/deliveries/queue/]
  │
  └─► Invalid credentials (wrong password OR email not found)
        └─► [Screen: Login] — inline generic error banner (no enumeration)
```

### 1.2 Logout Flow (UC-02 · US-02 · FR-01.5)

```
[Any authenticated screen] → "Cerrar sesión" link (global nav)
  └─► POST /accounts/logout/
        └─► Session destroyed → [Screen: Login]

[Any protected route after logout]
  └─► 302 Redirect → [Screen: Login]
```

### 1.3 Password Reset Flow (UC-03 · US-03 · FR-01.3, FR-01.4, FR-01.6)

```
[Screen: Login] → "¿Olvidaste tu contraseña?" link
  └─► [Screen: Password Reset — Request]
        ├─► Email exists in DB
        │     └─► Token generated (1h TTL, single-use)
        │           └─► Email dispatched via Resend SMTP
        │                 └─► [Screen: Login] — silent success message
        │
        └─► Email NOT found
              └─► [Screen: Login] — same silent success message (no enumeration)

[User clicks link in email] → /accounts/password-reset/<token>/
  ├─► Token valid (not used, not expired)
  │     └─► [Screen: Set New Password]
  │           ├─► Passwords match & meet rules
  │           │     └─► POST → token marked used → [Screen: Login] — success banner
  │           └─► Validation error
  │                 └─► [Screen: Set New Password] — inline field error
  │
  ├─► Token already used
  │     └─► [Screen: Token Error] — "este enlace ya fue utilizado"
  │
  └─► Token expired
        └─► [Screen: Token Error] — "el enlace ha expirado, solicita uno nuevo"
              └─► Link → [Screen: Password Reset — Request]
```

---

## 2. DISTRIBUTOR Flows

### 2.1 User Management (US-24 · FR-02.1)

```
[Distributor Dashboard]
  └─► "Usuarios" nav item → [Screen: User List]
        ├─► "Nuevo Usuario" button → [Screen: Create User Form]
        │     ├─► Valid submit → User created → [Screen: User List] + success toast
        │     ├─► Validation error → [Screen: Create User Form] — inline errors
        │     └─► "Cancelar" → [Screen: User List]
        │
        └─► Row action "Editar" → [Screen: Edit User Form]
              ├─► Role / active status changed → [Screen: User List] + success toast
              └─► "Cancelar" → [Screen: User List]
```

### 2.2 Product Catalog (UC-04 · US-04, US-05, US-06 · FR-03.1–FR-03.4)

```
[Distributor Dashboard]
  └─► "Catálogo" nav item → [Screen: Product List]
        ├─► "Nuevo Producto" button → [Screen: Create Product Form]
        │     ├─► Valid submit → Product saved → [Screen: Product List] + success toast
        │     └─► Validation error → inline field errors; product NOT saved
        │
        ├─► Row action "Editar" → [Screen: Edit Product Form]
        │     ├─► Valid submit → Product updated → [Screen: Product List] + toast
        │     └─► Validation error → inline field errors
        │
        ├─► Row action "Desactivar" (is_active=True)
        │     └─► Confirmation modal → confirm
        │           └─► is_active set to False → row badge changes to "Inactivo"
        │                 (AuditLog entry written)
        │
        └─► Row action "Reactivar" (is_active=False)
              └─► is_active set to True → row badge changes to "Activo"
                    (AuditLog entry written)
```

### 2.3 Vendor Inventory Assignment (UC-05 · US-07 · FR-03.5, FR-04.1)

```
[Distributor Dashboard]
  └─► "Inventario" nav item → [Screen: Inventory Overview]
        └─► "Asignar Stock" button → [Screen: Assign Inventory Form]
              ├─► Select vendor (dropdown) + product (dropdown) + quantity (number)
              ├─► Valid submit (qty ≥ 0)
              │     └─► VendorInventory upserted → [Screen: Inventory Overview] + toast
              ├─► qty = 0 → product removed from vendor inventory (confirm modal)
              └─► qty < 0 → inline validation error; NOT submitted
```

### 2.4 Store Management

```
[Distributor Dashboard]
  └─► "Tiendas" nav item → [Screen: Store List]
        ├─► "Nueva Tienda" button → [Screen: Create Store Form]
        │     └─► Valid submit → Store created → [Screen: Store List] + toast
        │
        └─► Row action "Editar" → [Screen: Edit Store Form]
              ├─► Assign/change vendor (dropdown — nullable, per DR-01)
              └─► Valid submit → [Screen: Store List] + toast
```

### 2.5 Operations Dashboard (UC-06 · US-08 · FR-08.1, FR-08.3)

```
[Distributor Dashboard]
  └─► "Dashboard" nav item → [Screen: Operations Dashboard]
        ├─► Orders table (grouped by status: PENDING / ACCEPTED /
        │   DISPATCHED / DELIVERED / REJECTED)
        │     └─► Row click → [Screen: Order Detail (Distributor view)]
        │                       └─► "Ver Auditoría" → [Screen: Audit Log (Order)]
        │
        ├─► Inventory grid (product × vendor matrix with low-stock badges)
        │     └─► Low-stock alert badge visible when qty < low_stock_threshold
        │
        └─► Filters panel (FR-08.2)
              ├─► Date range picker
              ├─► Vendor dropdown
              ├─► Store dropdown
              └─► Status multi-select → "Aplicar filtros" → table refreshes
```

### 2.6 Audit Log Consultation (UC-07 · US-09 · FR-09.5)

```
[Screen: Order Detail (Distributor view)]
  └─► "Ver Auditoría" button → [Screen: Audit Log (Order)]
        └─► Chronological list of events
              (timestamp · actor name + role · action · prev_status → new_status)
              (append-only — no delete/edit controls shown)
```

---

## 3. VENDOR Flows

### 3.1 Vendor Dashboard — Pending Orders (UC-10 · US-10 · FR-06.1, FR-06.6, FR-10.1)

```
[Screen: Vendor Dashboard]
  ├─► JS polls GET /api/orders/pending/ every 30 s
  │     └─► New order arrives → row appended to table without page reload
  │
  └─► Row click on pending order → [Screen: Order Detail (Vendor)]
```

### 3.2 Accept Order (UC-11 · US-11 · FR-04.3, FR-04.4, FR-06.2–FR-06.4)

```
[Screen: Order Detail (Vendor)] — order in PENDING status
  └─► "Aceptar" button
        └─► Confirmation modal: "¿Confirmar aceptación?"
              ├─► Confirm → POST /orders/<id>/accept/
              │     ├─► Stock sufficient (atomic transaction)
              │     │     └─► Inventory deducted · Status → ACCEPTED
              │     │           AuditLog written · Notification to store owner
              │     │           └─► [Screen: Vendor Dashboard] + success toast
              │     │
              │     └─► Insufficient stock (transaction rolled back)
              │           └─► [Screen: Order Detail (Vendor)] — per-item error banner
              │                 Order remains PENDING
              │
              └─► Cancel modal → [Screen: Order Detail (Vendor)] — no change
```

### 3.3 Reject Order (UC-12 · US-12 · FR-06.2, FR-06.4)

```
[Screen: Order Detail (Vendor)] — order in PENDING status
  └─► "Rechazar" button
        └─► [Modal: Reject Confirmation]
              ├─► Optional: textarea "Motivo del rechazo" (max 500 chars)
              ├─► Confirm → POST /orders/<id>/reject/
              │     └─► Status → REJECTED
              │           AuditLog written (prev=PENDING, new=REJECTED)
              │           Notification to store owner (with reason if provided)
              │           └─► [Screen: Vendor Dashboard] + toast
              │
              └─► Cancel → modal closes → [Screen: Order Detail (Vendor)]
```

### 3.4 Dispatch Order (UC-13 · US-13 · FR-06.5)

```
[Screen: Order Detail (Vendor)] — order in ACCEPTED status
  └─► "Marcar como Despachado" button
        └─► Confirmation modal: "¿Confirmar despacho?"
              ├─► Confirm → POST /orders/<id>/dispatch/
              │     └─► Status → DISPATCHED
              │           AuditLog written
              │           Notification to store owner
              │           Order now visible in delivery queue
              │           └─► [Screen: Vendor Dashboard] + toast
              │
              └─► Cancel → modal closes
```

### 3.5 Vendor Inventory View (UC-09 · FR-04.2)

```
[Screen: Vendor Dashboard]
  └─► "Mi Inventario" nav item → [Screen: Vendor Inventory]
        └─► Read-only table: product name · assigned quantity
              (only own inventory; other vendors' data never visible)
```

---

## 4. STORE_OWNER Flows

### 4.1 Place Order (UC-14 · US-14 · FR-05.1, FR-05.3, FR-05.4 · DR-01)

```
[Screen: Store Owner Dashboard]
  └─► "Nuevo Pedido" button
        │
        ├─► Store has NO vendor assigned (DR-01 edge case)
        │     └─► Button is DISABLED — tooltip/message:
        │           "Tu tienda no tiene un vendedor asignado. Contacta al distribuidor."
        │
        └─► Store HAS vendor assigned
              │
              ├─► Store owner belongs to MULTIPLE stores
              │     └─► [Step 0: Select Store] — radio list of stores
              │           └─► "Continuar" → [Step 1: Select Products]
              │
              └─► Store owner belongs to SINGLE store
                    └─► [Step 1: Select Products]
                          └─► Product grid (only vendor's active inventory shown)
                                Each row: product name · unit price · quantity stepper (min 1)
                                ├─► qty = 0 for any item → "Continuar" stays disabled
                                └─► At least 1 item with qty ≥ 1 → "Continuar" enabled
                                      └─► [Step 2: Review Order]
                                            ├─► Table: product · qty · price per unit · subtotal
                                            ├─► Order total
                                            ├─► "Editar" → back to [Step 1]
                                            └─► "Confirmar Pedido" button
                                                  └─► POST /orders/
                                                        ├─► All products available
                                                        │     └─► Order created (PENDING)
                                                        │           unitPriceAtTime captured
                                                        │           └─► [Step 3: Confirmation]
                                                        │                 "Tu pedido fue enviado."
                                                        │                 "Número de pedido: #XXXX"
                                                        │                 → "Ver mis pedidos" link
                                                        │
                                                        └─► Product(s) not in vendor inventory
                                                              └─► [Step 2] — per-item error banner
                                                                    Order NOT created
```

### 4.2 Track Order Status (UC-15 · US-15 · FR-05.5)

```
[Screen: Store Owner Dashboard]
  └─► "Mis Pedidos" nav item → [Screen: Order History]
        └─► List of orders (newest first)
              Each row: order # · date · status badge · store name
              └─► Row click → [Screen: Order Detail (Store Owner)]
                    ├─► Status: PENDING
                    │     └─► "Cancelar pedido" button (US-23)
                    │
                    ├─► Status: REJECTED
                    │     └─► "Reenviar pedido" button (US-22)
                    │
                    └─► Status: ACCEPTED / DISPATCHED / DELIVERED
                          └─► Read-only detail view
```

### 4.3 Cancel Pending Order (US-23)

```
[Screen: Order Detail (Store Owner)] — status = PENDING
  └─► "Cancelar pedido" button
        └─► Confirmation modal: "¿Estás seguro? Esta acción no se puede deshacer."
              ├─► Confirm → POST /orders/<id>/cancel/
              │     └─► Status → REJECTED
              │           rejection_reason = "Cancelado por el propietario de la tienda"
              │           AuditLog written (prev=PENDING, new=REJECTED)
              │           Inventory unchanged
              │           └─► [Screen: Order History] + toast
              │
              └─► Cancel modal → no change
```

### 4.4 Resubmit Rejected Order (US-22)

```
[Screen: Order Detail (Store Owner)] — status = REJECTED
  └─► "Reenviar pedido" button
        └─► Confirmation modal: "Se creará un nuevo pedido con los mismos productos."
              ├─► Confirm → POST /orders/<id>/resubmit/
              │     └─► New Order created (PENDING)
              │           previousOrderId → rejected order's ID
              │           Items cloned with CURRENT catalog prices
              │           Vendor from current store.vendor (may differ from original)
              │           └─► [Screen: Order Detail (Store Owner)] — NEW order
              │                 "Pedido reenviado. Número: #XXXX"
              │
              └─► Cancel modal → no change
```

### 4.5 Notifications (US-16 · FR-10.2–FR-10.4 · DR-03)

```
[Any Store Owner screen]
  └─► Notification bell icon (nav) — unread count badge (loaded on page load)
        └─► Click → [Screen: Notification Center]
              ├─► List: message · order reference · timestamp · read/unread indicator
              └─► "Marcar como leída" action per notification (or "Marcar todas")
                    └─► Notification.is_read = True → count badge decremented
```

---

## 5. DELIVERY Flows

### 5.1 Dispatched Orders Queue (UC-16 · US-17 · FR-07.1)

```
[Screen: Delivery Dashboard / Queue]
  └─► List of all DISPATCHED orders (same-distributor, first-come-first-served, DR-02)
        Each row: store name · store address · product summary · order date
        └─► Row click → [Screen: Delivery Order Detail]
```

### 5.2 Confirm Delivery with Photo (UC-17 · US-18 · FR-07.2–FR-07.5)

```
[Screen: Delivery Order Detail] — order in DISPATCHED status
  └─► "Confirmar Entrega" button
        └─► [Screen: Delivery Confirmation Form]
              │
              ├─► Step A: Photo upload widget (browser-direct to Cloudinary upload preset)
              │     ├─► No photo uploaded → "Confirmar" button is DISABLED
              │     └─► Photo uploaded → Cloudinary returns public_id
              │                           → public_id stored in hidden field
              │                           → "Confirmar" button ENABLED
              │
              └─► Step B: Submit form
                    └─► POST /deliveries/<id>/confirm/  { public_id: "..." }
                          ├─► public_id valid (Cloudinary SDK verifies origin)
                          │     └─► DeliveryConfirmation record created
                          │           Status → DELIVERED
                          │           AuditLog written
                          │           └─► [Screen: Delivery Dashboard] + success toast
                          │
                          └─► public_id invalid / externally supplied
                                └─► [Screen: Delivery Confirmation Form]
                                      — error: "La foto debe ser tomada desde esta aplicación."
                                      Order remains DISPATCHED
```

---

## 6. Conceptual Wireframes

---

### W-01 · Login Screen

**Route:** `/accounts/login/`  
**Accessible to:** All unauthenticated users

**Layout Structure:**
```
┌─────────────────────────────────────────┐
│           HEADER / BRAND                │
│         [ISBER Solutions Logo]          │
│         "Plataforma de Distribución"    │
├─────────────────────────────────────────┤
│                                         │
│         ┌───────────────────────┐       │
│         │    LOGIN CARD         │       │
│         │                       │       │
│         │  [Error Banner]       │       │  ← only shown on failed attempt
│         │                       │       │
│         │  Label: Correo        │       │
│         │  [Email Input]        │       │
│         │                       │       │
│         │  Label: Contraseña    │       │
│         │  [Password Input]     │       │
│         │                       │       │
│         │  [Btn: Iniciar sesión]│       │  ← Primary, full-width
│         │                       │       │
│         │  [Link: ¿Olvidaste    │       │
│         │   tu contraseña?]     │       │
│         └───────────────────────┘       │
│                                         │
└─────────────────────────────────────────┘
```

**UI Components Inventory:**

| Component | Type | Notes |
|-----------|------|-------|
| Logo / App name | Image + Heading | Centered branding block |
| Error banner | Alert (danger) | Generic: "Credenciales incorrectas." Hidden by default |
| Email field | `<input type="email">` + `<label>` | Required; visible label (NFR-04.7) |
| Password field | `<input type="password">` + `<label>` | Required; visible label |
| Submit button | Primary button (full-width) | Label: "Iniciar sesión" |
| Forgot password link | Anchor text | Routes to W-02 |

**Component States & Behaviors:**

- **Error banner:** Hidden on load; visible after failed POST; disappears when user starts typing again.
- **Submit button:** Enabled at all times; validation errors returned server-side.
- **Email/Password inputs:** No client-side enumeration — both fields clear only password on error.

---

### W-02 · Password Reset — Request

**Route:** `/accounts/password-reset/`

**Layout Structure:**
```
┌─────────────────────────────────────────┐
│           HEADER / BRAND                │
├─────────────────────────────────────────┤
│         ┌───────────────────────┐       │
│         │   PASSWORD RESET CARD │       │
│         │                       │       │
│         │  [Info banner]        │       │  ← "Ingresa tu correo para recibir
│         │                       │       │       un enlace de recuperación."
│         │  Label: Correo        │       │
│         │  [Email Input]        │       │
│         │                       │       │
│         │  [Btn: Enviar enlace] │       │  ← Primary
│         │  [Link: Volver]       │       │  ← Secondary text link → W-01
│         └───────────────────────┘       │
│                                         │
│         [Success banner — post submit]  │  ← "Si el correo existe, recibirás
│         (always shown, avoids enum.)    │      un enlace en los próximos minutos."
└─────────────────────────────────────────┘
```

**UI Components Inventory:**

| Component | Type | Notes |
|-----------|------|-------|
| Info banner | Alert (info) | Instructional text |
| Email field | `<input type="email">` + `<label>` | Required |
| Submit button | Primary button (full-width) | Label: "Enviar enlace" |
| Back link | Anchor text | Routes to W-01 |
| Success banner | Alert (success) | Always shown after POST regardless of email existence |

**Component States & Behaviors:**

- **Success banner:** Replaces form on POST success; no indication of whether email was found.
- **Submit button:** Loading spinner state during POST.

---

### W-03 · Set New Password

**Route:** `/accounts/password-reset/<token>/`

**Layout Structure:**
```
┌─────────────────────────────────────────┐
│           HEADER / BRAND                │
├─────────────────────────────────────────┤
│         ┌───────────────────────┐       │
│         │  SET NEW PASSWORD CARD│       │
│         │                       │       │
│         │  [Error banner]       │       │  ← token already used / expired
│         │                       │       │
│         │  Label: Nueva contr.  │       │
│         │  [Password Input]     │       │
│         │  [Validation hint]    │       │
│         │                       │       │
│         │  Label: Confirmar     │       │
│         │  [Password Input]     │       │
│         │  [Match error msg]    │       │
│         │                       │       │
│         │  [Btn: Guardar]       │       │  ← Primary; disabled until both fields valid
│         └───────────────────────┘       │
└─────────────────────────────────────────┘
```

**UI Components Inventory:**

| Component | Type | Notes |
|-----------|------|-------|
| Token error banner | Alert (danger) | "este enlace ya fue utilizado" or "el enlace ha expirado…" |
| New password field | `<input type="password">` + `<label>` | Required |
| Confirm password field | `<input type="password">` + `<label>` | Must match |
| Inline mismatch error | Validation message (danger) | Shown below confirm field |
| Submit button | Primary button | Disabled until passwords match |
| Link to request new reset | Anchor text | Shown only on expired token error |

---

### W-04 · Global Navigation Shell (Authenticated)

All authenticated screens share this shell. Role determines which nav items appear.

**Layout Structure:**
```
┌──────────────────────────────────────────────────────┐
│  TOP NAV BAR                                         │
│  [Logo]  [Nav items per role]       [Bell 🔔 3]  [👤 Nombre · Rol · Cerrar sesión] │
├──────────┬───────────────────────────────────────────┤
│ SIDEBAR  │  MAIN CONTENT AREA                        │
│ (desktop)│                                           │
│          │  [Page title]                             │
│ Nav      │                                           │
│ items    │  [Content]                                │
│ (list)   │                                           │
│          │                                           │
└──────────┴───────────────────────────────────────────┘
```

**Nav items by role:**

| DISTRIBUTOR | VENDOR | STORE_OWNER | DELIVERY |
|-------------|--------|-------------|----------|
| Dashboard | Dashboard | Nuevo Pedido | Cola de Entregas |
| Catálogo | Mi Inventario | Mis Pedidos | — |
| Inventario | — | Notificaciones | — |
| Tiendas | — | — | — |
| Usuarios | — | — | — |

**Component States & Behaviors:**

- **Notification bell (🔔):** Visible only for STORE_OWNER. Badge count = unread notifications. Loaded on every page load (no polling for store owners per DR-03).
- **Sidebar:** Collapses to hamburger menu on screens < 360 px wide (NFR-04.2).
- **Active nav item:** Highlighted/underlined to indicate current section.
- **Role badge:** User name and role shown next to avatar/initials in top-right.

---

### W-05 · Distributor Operations Dashboard

**Route:** `/catalog/dashboard/` (or `/distributor/dashboard/`)  
**Role:** DISTRIBUTOR

**Layout Structure:**
```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  Dashboard de Operaciones                                         │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  FILTERS BAR                                                │  │
│  │  [Date range picker] [Vendor ▼] [Store ▼] [Status ▼] [Aplicar] │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  SUMMARY METRICS ROW                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ PENDING  │  │ACCEPTED  │  │DISPATCHED│  │DELIVERED │         │
│  │   12     │  │   5      │  │   3      │  │   48     │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
│                                                                   │
│  ORDERS TABLE                                                     │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ # │ Store │ Vendor │ Date │ Items │ Status │ Actions      │   │
│  │ ─ │ ───── │ ────── │ ──── │ ───── │ ────── │ ─────────── │   │
│  │001│Tienda1│ Juan   │01/07 │  3    │PENDING │ [Ver]        │   │
│  │002│Tienda2│ Pedro  │01/07 │  1    │DELIVERED│[Ver]        │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  INVENTORY OVERVIEW                                               │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ Product       │ Vendor A │ Vendor B │ Vendor C            │   │
│  │ ──────────    │ ──────── │ ──────── │ ──────────          │   │
│  │ Coca-Cola     │  120     │ ⚠️ 3      │   45               │   │  ← low-stock badge
│  │ Pepsi 2L      │   50     │   80     │ ⚠️ 2                │   │
│  └───────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

**UI Components Inventory:**

| Component | Type | Notes |
|-----------|------|-------|
| Filters bar | Row of form controls | Date range, 3 dropdowns, apply button |
| Summary metric cards | Stat cards (4) | PENDING · ACCEPTED · DISPATCHED · DELIVERED counts |
| Orders data table | Table w/ pagination | Sortable columns; "Ver" links to order detail |
| Low-stock badge | Inline badge (warning ⚠️) | Shown when qty < `low_stock_threshold` (DR-05) |
| Inventory grid | Table | Rows = products; columns = vendors; cells = quantity |

**Component States & Behaviors:**

- **Summary cards:** Click on a card pre-filters the orders table to that status.
- **Low-stock badge:** Color: amber/orange. Tooltip shows threshold value.
- **"Ver" link:** Opens W-13 (Order Detail — Distributor view).
- **Filters bar "Aplicar":** Loading spinner while table refreshes.

---

### W-06 · Product List (Distributor)

**Route:** `/catalog/products/`  
**Role:** DISTRIBUTOR

**Layout Structure:**
```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  Catálogo de Productos                    [+ Nuevo Producto]      │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ [Search input: "Buscar producto..."]                      │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ Name │ Description │ Unit Price │ Threshold │ Status │ Actions│
│  │ ──── │ ─────────── │ ────────── │ ───────── │ ────── │ ─────── │
│  │Coca-C│ Bebida gaseosa│  $1.50   │     5     │ ✅ Activo│[Editar][Desactivar]│
│  │Pepsi │ Bebida gaseosa│  $1.40   │    10     │ ❌ Inactivo│[Editar][Reactivar]│
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  [Pagination controls]                                            │
└───────────────────────────────────────────────────────────────────┘
```

**UI Components Inventory:**

| Component | Type | Notes |
|-----------|------|-------|
| Page header + "Nuevo Producto" | H1 + Primary button | Top-right button |
| Search input | `<input type="search">` | Client-side filter |
| Products table | Data table | Sortable; paginated |
| Status badge | Badge (green=Activo / gray=Inactivo) | Per DR-06 |
| "Editar" | Secondary button per row | Opens W-07 |
| "Desactivar" / "Reactivar" | Danger / Success button per row | Triggers confirmation modal |

**Component States & Behaviors:**

- **"Desactivar":** Triggers confirmation modal before setting `is_active=False`. AuditLog written.
- **"Reactivar":** No confirmation needed; sets `is_active=True` immediately.
- **Inactive rows:** Row visually dimmed (reduced opacity) to signal inactivity.

---

### W-07 · Create / Edit Product Form

**Route:** `/catalog/products/new/` · `/catalog/products/<id>/edit/`  
**Role:** DISTRIBUTOR

**Layout Structure:**
```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  ← Volver al Catálogo                                             │
│  Nuevo Producto  /  Editar Producto                               │
│                                                                   │
│  ┌─────────────────────────────────────────┐                      │
│  │  Label: Nombre del producto *           │                      │
│  │  [Text Input]                           │                      │
│  │  [Validation error msg]                 │                      │
│  │                                         │                      │
│  │  Label: Descripción *                   │                      │
│  │  [Textarea]                             │                      │
│  │  [Validation error msg]                 │                      │
│  │                                         │                      │
│  │  Label: Precio unitario (USD) *         │                      │
│  │  [Number Input — min 0.01]              │                      │
│  │  [Validation error msg]                 │                      │
│  │                                         │                      │
│  │  Label: Umbral de stock bajo *          │                      │
│  │  [Number Input — min 0, default 5]      │                      │
│  │  Helper: "El dashboard alertará cuando  │                      │
│  │  el stock caiga por debajo de este valor"│                     │
│  │                                         │                      │
│  │  [Btn: Guardar producto]  [Btn: Cancelar]│                     │
│  └─────────────────────────────────────────┘                      │
└───────────────────────────────────────────────────────────────────┘
```

**UI Components Inventory:**

| Component | Type | Notes |
|-----------|------|-------|
| Back link | Anchor | Returns to W-06 |
| Name field | `<input type="text">` + `<label>` | Required |
| Description field | `<textarea>` + `<label>` | Required |
| Unit price field | `<input type="number" step="0.01" min="0.01">` | Required |
| Low-stock threshold | `<input type="number" min="0">` + helper text | Default: 5 (DR-05, US-25) |
| Inline validation errors | Error text below each field | Per-field messages |
| Save button | Primary button | Label: "Guardar producto" |
| Cancel button | Secondary/ghost button | Returns to W-06 without saving |

**Component States & Behaviors:**

- **Save button:** Disabled during POST submission (prevents double-submit). Loading spinner shown.
- **Price field on Edit:** Change reflected immediately in catalog; existing `unitPriceAtTime` on past orders is preserved (US-05 acceptance criteria).

---

### W-08 · Assign Inventory to Vendor

**Route:** `/catalog/inventory/assign/`  
**Role:** DISTRIBUTOR

**Layout Structure:**
```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  Inventario — Asignar Stock               [+ Asignar Stock]      │
│                                                                   │
│  INVENTORY GRID                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ Product       │ Vendor A │ Vendor B │ Vendor C            │   │
│  │ ──────────    │ ──────── │ ──────── │ ──────────          │   │
│  │ Coca-Cola     │  120     │ ⚠️ 3      │   45               │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ASSIGN FORM PANEL (inline or modal)                              │
│  ┌─────────────────────────────────────────┐                      │
│  │  Label: Vendedor *                      │                      │
│  │  [Dropdown — vendors in distributor]    │                      │
│  │                                         │                      │
│  │  Label: Producto *                      │                      │
│  │  [Dropdown — active products only]      │                      │
│  │                                         │                      │
│  │  Label: Cantidad *                      │                      │
│  │  [Number Input — min 0]                 │                      │
│  │  Helper: "0 elimina el producto del     │                      │
│  │  inventario del vendedor"               │                      │
│  │                                         │                      │
│  │  [Btn: Guardar]  [Btn: Cancelar]        │                      │
│  └─────────────────────────────────────────┘                      │
└───────────────────────────────────────────────────────────────────┘
```

**UI Components Inventory:**

| Component | Type | Notes |
|-----------|------|-------|
| Inventory grid | Data table | Read-only; low-stock ⚠️ badges |
| Vendor dropdown | `<select>` + `<label>` | Scoped to distributor's vendors |
| Product dropdown | `<select>` + `<label>` | Active products only |
| Quantity field | `<input type="number" min="0">` | qty=0 removes the assignment |
| Negative qty error | Inline validation | "La cantidad no puede ser negativa" |
| Save button | Primary button | Upserts VendorInventory |
| Cancel button | Secondary button | Clears form |

---

### W-09 · User Management (Distributor)

**Route:** `/accounts/users/`  
**Role:** DISTRIBUTOR

**Layout Structure:**
```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  Usuarios de la Plataforma             [+ Nuevo Usuario]          │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ Name │ Email │ Role │ Active │ Created │ Actions           │   │
│  │ ──── │ ───── │ ──── │ ────── │ ─────── │ ────────────── │   │
│  │ Juan │ j@… │ VENDOR │ ✅ Sí  │ 01/06   │ [Editar]         │   │
│  │ Ana  │ a@… │STORE_OWNER│ ✅ Sí│ 15/06 │ [Editar]         │   │
│  └───────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

**Create / Edit User Form (modal or separate screen):**

| Field | Type | Notes |
|-------|------|-------|
| Full name | Text input | Required |
| Email | Email input | Required; unique |
| Password | Password input | Required on create; optional on edit |
| Role | Select dropdown | VENDOR · STORE_OWNER · DELIVERY (not DISTRIBUTOR) |
| Active | Toggle/checkbox | Default: true |

**Component States & Behaviors:**

- **Role dropdown:** DISTRIBUTOR option is hidden/absent per US-24 acceptance criteria.
- **"Editar" button:** Pre-populates form with current values; password field shows "Dejar en blanco para no cambiar."
- **Tenant isolation:** Users created here are scoped to the current distributor; never visible to other distributors.

---

### W-10 · Vendor Dashboard (with Polling)

**Route:** `/orders/vendor-dashboard/`  
**Role:** VENDOR

**Layout Structure:**
```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  Panel del Vendedor                                               │
│                                                                   │
│  PENDING ORDERS                        [Last updated: 14:32:05]  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ # │ Store │ Date │ Items │ Total │ Actions                 │   │
│  │ ─ │ ───── │ ──── │ ───── │ ───── │ ────────────────────── │   │
│  │001│Tienda1│01/07 │  3    │$45.00 │ [Ver pedido]           │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ACCEPTED ORDERS                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ # │ Store │ Accepted at │ Items │ Actions                  │   │
│  │ ─ │ ───── │ ─────────── │ ───── │ ────────────────────── │   │
│  │002│Tienda2│  13:20      │  1    │ [Ver pedido]            │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  MY INVENTORY                                                     │
│  ┌─────────────────────────────────────────┐                      │
│  │ Product     │ Available qty              │                      │
│  │ ─────────── │ ─────────────             │                      │
│  │ Coca-Cola   │     120                    │                      │
│  │ Pepsi 2L    │      50                    │                      │
│  └─────────────────────────────────────────┘                      │
└───────────────────────────────────────────────────────────────────┘
```

**UI Components Inventory:**

| Component | Type | Notes |
|-----------|------|-------|
| "Last updated" timestamp | Small text | Updated each poll cycle |
| Pending orders table | Data table | Polled every 30s via JS; rows added without reload |
| Accepted orders table | Data table | Static; shows orders ready to dispatch |
| My inventory table | Data table | Read-only; vendor's own stock only |
| "Ver pedido" button | Secondary button | Opens W-11 |
| New-order toast | Toast notification | Appears when poll finds new rows |

**Component States & Behaviors:**

- **JS Polling:** `setInterval(30000)` → `fetch('/api/orders/pending/')` → DOM update.
- **Empty pending table:** "No tienes pedidos pendientes en este momento." placeholder row.
- **New order sound/badge:** Optional visual pulse on the section heading when new row arrives.

---

### W-11 · Order Detail — Vendor View

**Route:** `/orders/<id>/` (vendor session)  
**Role:** VENDOR

**Layout Structure:**
```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  ← Volver al panel                                                │
│  Pedido #001 — PENDING                    [Status badge]         │
│                                                                   │
│  ORDER INFO                                                       │
│  ┌─────────────────────────────────────────┐                      │
│  │ Tienda: Tienda El Sol                   │                      │
│  │ Fecha: 01/07/2026, 14:00                │                      │
│  │ Vendedor asignado: Juan Pérez           │                      │
│  └─────────────────────────────────────────┘                      │
│                                                                   │
│  ORDER ITEMS                                                      │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ Product    │ Qty ordered │ Unit price │ Subtotal           │   │
│  │ ─────────  │ ─────────── │ ────────── │ ───────            │   │
│  │ Coca-Cola  │     10      │   $1.50    │  $15.00            │   │
│  │ Pepsi 2L   │      5      │   $1.40    │   $7.00            │   │
│  │            │             │  TOTAL:    │  $22.00            │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  [Inline stock error banner]  ← only on failed accept             │
│  "Stock insuficiente: Pepsi 2L (disponible: 3, solicitado: 5)"   │
│                                                                   │
│  ACTION BUTTONS  (shown according to current status)             │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ [Btn: Aceptar ✓]          [Btn: Rechazar ✗]               │   │  ← PENDING
│  │ [Btn: Marcar como Despachado]                              │   │  ← ACCEPTED
│  └───────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

**UI Components Inventory:**

| Component | Type | Notes |
|-----------|------|-------|
| Back link | Anchor | Returns to W-10 |
| Order info card | Info panel | Store, date, assigned vendor |
| Order items table | Data table | Product · qty · unit price · subtotal; total row |
| Stock error banner | Alert (danger) | Per-item errors on failed accept; hidden normally |
| "Aceptar" button | Success/primary button | Triggers confirmation modal → W-11a |
| "Rechazar" button | Danger button | Triggers reject modal → W-11b |
| "Marcar como Despachado" button | Warning/secondary button | Only when ACCEPTED; triggers confirm modal |

**Component States & Behaviors:**

- **Action buttons:** Rendered conditionally by server based on order status. PENDING: Aceptar + Rechazar. ACCEPTED: Marcar como Despachado. DISPATCHED/DELIVERED/REJECTED: no actions; read-only view.
- **"Aceptar" loading state:** Button shows spinner and is disabled during POST to prevent double-submission.

---

### W-11a · Modal: Confirm Order Accept

```
┌─────────────────────────────────────┐
│  Confirmar aceptación               │
│  ─────────────────────────────────  │
│  ¿Deseas aceptar el Pedido #001?    │
│  Se descontará el inventario        │
│  correspondiente.                   │
│                                     │
│  [Btn: Confirmar]  [Btn: Cancelar]  │
└─────────────────────────────────────┘
```

---

### W-11b · Modal: Confirm Order Reject

```
┌─────────────────────────────────────┐
│  Rechazar pedido                    │
│  ─────────────────────────────────  │
│  Label: Motivo del rechazo          │
│  [Textarea — optional, max 500 ch.] │
│                                     │
│  [Btn: Rechazar pedido] [Cancelar]  │
└─────────────────────────────────────┘
```

**Component States & Behaviors:**
- **Textarea:** Optional. If empty, Notification to store owner omits the reason.
- **"Rechazar pedido" button:** Primary danger style. Loading state on click.

---

### W-12 · Store Owner Dashboard

**Route:** `/orders/store-dashboard/`  
**Role:** STORE_OWNER

**Layout Structure:**
```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  Panel de Tienda                                                  │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  NOTIFICATIONS BANNER (if unread > 0)                       │  │
│  │  "Tienes 3 notificaciones sin leer." [Ver notificaciones]   │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  QUICK ACTIONS                                                    │
│  ┌──────────────────────────────┐                                │
│  │  [Btn: + Nuevo Pedido]       │  ← PRIMARY, large (48px tap)  │
│  │  (disabled if no vendor)     │                                │
│  └──────────────────────────────┘                                │
│  [If no vendor: "Tu tienda no tiene un vendedor asignado.        │
│   Contacta al distribuidor."]                                     │
│                                                                   │
│  RECENT ORDERS                                                    │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ # │ Date │ Items │ Status │ Actions                        │   │
│  │ ─ │ ──── │ ───── │ ────── │ ─────────────────────────── │   │
│  │001│01/07 │  3    │PENDING │ [Ver] [Cancelar]              │   │
│  │002│28/06 │  1    │DELIVERED│[Ver]                         │   │
│  └───────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

**UI Components Inventory:**

| Component | Type | Notes |
|-----------|------|-------|
| Notifications banner | Alert (info) | Shown only if unread > 0; links to W-16 |
| "Nuevo Pedido" button | Primary button (large) | Min 48×48 px (NFR-04.3); disabled state if no vendor |
| No-vendor message | Info text | Shown below disabled button per DR-01 |
| Recent orders table | Data table | Last 10 orders; full list at "Mis Pedidos" |
| Status badge | Colored badge | PENDING=yellow · ACCEPTED=blue · DISPATCHED=orange · DELIVERED=green · REJECTED=red |
| "Ver" button | Secondary button | Opens W-15 |
| "Cancelar" button | Danger button | Only for PENDING orders; opens cancel modal |

---

### W-13 · Place Order — Step 0: Select Store

**Route:** `/orders/new/` → step 0  
**Role:** STORE_OWNER (when owner belongs to multiple stores)

```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  Nuevo Pedido — Paso 1 de 3                                       │
│  [Step indicator: ● — — ]                                         │
│                                                                   │
│  ¿Para qué tienda es el pedido?                                   │
│                                                                   │
│  ┌─────────────────────────────────────────┐                      │
│  │  ○  Tienda El Sol — Calle 10, Loja      │                      │
│  │  ○  Tienda La Luna — Av. Universitaria  │                      │
│  └─────────────────────────────────────────┘                      │
│                                                                   │
│  [Btn: Continuar]  ← disabled until a store is selected          │
└───────────────────────────────────────────────────────────────────┘
```

---

### W-14 · Place Order — Step 1: Select Products

**Route:** `/orders/new/` → step 1  
**Role:** STORE_OWNER

```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  Nuevo Pedido — Paso 2 de 3                                       │
│  [Step indicator: ✓ ● — ]                                         │
│                                                                   │
│  Selecciona los productos                                         │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ Product    │ Unit price │ Qty                              │   │
│  │ ─────────  │ ────────── │ ─────────────────────────────── │   │
│  │ Coca-Cola  │   $1.50    │ [ - ] [ 0 ] [ + ]               │   │
│  │ Pepsi 2L   │   $1.40    │ [ - ] [ 0 ] [ + ]               │   │
│  │ Agua 500ml │   $0.80    │ [ - ] [ 0 ] [ + ]               │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  [Btn: Ver resumen →]  ← disabled if all qty = 0                 │
└───────────────────────────────────────────────────────────────────┘
```

**Component States & Behaviors:**

- **Quantity stepper:** Min value = 0 (typing or decrement below 0 is blocked). Min tap target 48×48 px.
- **"Ver resumen" button:** Enabled only when at least one product has qty ≥ 1.
- **Product list:** Only active products from assigned vendor's inventory shown.

---

### W-15 · Place Order — Step 2: Review & Confirm

**Route:** `/orders/new/` → step 2

```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  Nuevo Pedido — Paso 3 de 3                                       │
│  [Step indicator: ✓ ✓ ● ]                                         │
│                                                                   │
│  Resumen del pedido                                               │
│                                                                   │
│  [Stock error banner — if any item unavailable after submit]      │
│  "Pepsi 2L no está disponible en el inventario del vendedor."     │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ Product    │ Qty │ Unit price │ Subtotal                   │   │
│  │ ─────────  │ ─── │ ────────── │ ──────────                 │   │
│  │ Coca-Cola  │  10 │   $1.50    │  $15.00                    │   │
│  │ Pepsi 2L   │   5 │   $1.40    │   $7.00                    │   │
│  │            │     │  TOTAL:    │  $22.00                    │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  [← Editar productos]    [Btn: Confirmar Pedido ✓]              │
│                          ← Primary; min 48×48 px                 │
└───────────────────────────────────────────────────────────────────┘
```

---

### W-15b · Place Order — Step 3: Confirmation

```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  ✅  ¡Pedido enviado exitosamente!                                │
│                                                                   │
│  Número de pedido: #001                                           │
│  Tienda: Tienda El Sol                                            │
│  El vendedor revisará tu pedido pronto.                           │
│                                                                   │
│  [Btn: Ver mis pedidos]   [Btn: Nuevo pedido]                    │
└───────────────────────────────────────────────────────────────────┘
```

---

### W-16 · Order Detail — Store Owner View

**Route:** `/orders/<id>/` (store owner session)  
**Role:** STORE_OWNER

```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  ← Mis Pedidos                                                    │
│  Pedido #001                              [Status badge: PENDING] │
│                                                                   │
│  ┌─────────────────────────────────────────┐                      │
│  │ Tienda: Tienda El Sol                   │                      │
│  │ Fecha: 01/07/2026, 14:00                │                      │
│  │ Vendedor: Juan Pérez                    │                      │
│  └─────────────────────────────────────────┘                      │
│                                                                   │
│  ORDER ITEMS TABLE  (same as W-11)                                │
│                                                                   │
│  STATUS TIMELINE                                                  │
│  ┌─────────────────────────────────────────┐                      │
│  │ ✅ Creado — 01/07 14:00                 │                      │
│  │ ⏳ Esperando al vendedor…               │                      │
│  └─────────────────────────────────────────┘                      │
│                                                                   │
│  ACTIONS (contextual by status)                                   │
│  PENDING:     [Btn: Cancelar pedido]                              │
│  REJECTED:    [Motivo: "..."]  [Btn: Reenviar pedido]            │
│  Others:      (read-only)                                         │
└───────────────────────────────────────────────────────────────────┘
```

---

### W-17 · Notification Center — Store Owner

**Route:** `/accounts/notifications/`  
**Role:** STORE_OWNER

```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  Notificaciones                     [Marcar todas como leídas]   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ 🔵 [Nuevo] Tu Pedido #001 fue ACEPTADO       01/07 14:10  │   │  ← unread
│  │    [Ver pedido]                                           │   │
│  ├───────────────────────────────────────────────────────────┤   │
│  │ ⬜ Tu Pedido #002 fue DESPACHADO              30/06 09:00  │   │  ← read
│  │    [Ver pedido]                                           │   │
│  └───────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

**UI Components Inventory:**

| Component | Type | Notes |
|-----------|------|-------|
| "Marcar todas" button | Secondary button | Sets all `is_read=True`; badge → 0 |
| Notification row | List item | Blue dot = unread; grey = read |
| "Ver pedido" link | Anchor | Routes to W-16 for that order |
| Empty state | Illustration + text | "No tienes notificaciones." |

---

### W-18 · Delivery Queue

**Route:** `/deliveries/queue/`  
**Role:** DELIVERY

```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  Cola de Entregas                                                 │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ # │ Store │ Address │ Products │ Date │ Actions            │   │
│  │ ─ │ ───── │ ─────── │ ──────── │ ──── │ ────────────────── │   │
│  │003│Tienda1│Calle 10 │ 3 items  │01/07 │ [Confirmar entrega]│   │
│  │004│Tienda2│Av. Univ.│ 1 item   │01/07 │ [Confirmar entrega]│   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  [Empty state: "No hay pedidos despachados en este momento."]     │
└───────────────────────────────────────────────────────────────────┘
```

---

### W-19 · Delivery Confirmation Form

**Route:** `/deliveries/<id>/confirm/`  
**Role:** DELIVERY

```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  ← Cola de entregas                                               │
│  Confirmar Entrega — Pedido #003                                  │
│                                                                   │
│  ORDER SUMMARY                                                    │
│  ┌─────────────────────────────────────────┐                      │
│  │ Tienda: Tienda El Sol                   │                      │
│  │ Dirección: Calle 10 de Agosto           │                      │
│  │ Productos: Coca-Cola x10, Pepsi x5      │                      │
│  └─────────────────────────────────────────┘                      │
│                                                                   │
│  PHOTO UPLOAD                                                     │
│  ┌─────────────────────────────────────────┐                      │
│  │  [Photo upload widget — Cloudinary]     │  ← browser-direct   │
│  │                                         │     upload to preset │
│  │  [Empty state: camera icon + ]          │                      │
│  │   "Toma una foto como prueba de         │                      │
│  │    entrega"]                            │                      │
│  │                                         │                      │
│  │  [After upload: thumbnail preview]      │                      │
│  │  [Hidden input: public_id value]        │                      │
│  └─────────────────────────────────────────┘                      │
│                                                                   │
│  [Error banner — invalid public_id]                               │
│  "La foto debe ser tomada desde esta aplicación."                │
│                                                                   │
│  [Btn: Confirmar Entrega ✓]  ← DISABLED until photo uploaded     │
│                               Min 48×48 px; primary style        │
└───────────────────────────────────────────────────────────────────┘
```

**UI Components Inventory:**

| Component | Type | Notes |
|-----------|------|-------|
| Order summary card | Info panel | Store name, address, product summary |
| Cloudinary upload widget | Third-party widget / `<input type="file">` styled | Browser-direct upload to Cloudinary upload preset |
| Photo thumbnail preview | `<img>` | Shown after successful upload |
| Hidden `public_id` field | `<input type="hidden">` | Populated by Cloudinary callback |
| Invalid photo error | Alert (danger) | Shown on server-side rejection |
| "Confirmar Entrega" button | Primary button | Disabled until `public_id` is populated in DOM |

**Component States & Behaviors:**

- **Before upload:** Button is `disabled`; upload widget shows instructional placeholder.
- **After upload:** Thumbnail visible; `public_id` hidden field filled; button enabled.
- **On server rejection:** Button re-enables; error banner shown; photo must be re-taken.
- **Loading state:** Button shows spinner and is disabled during POST.

---

### W-20 · Order Detail — Distributor View (with Audit)

**Route:** `/orders/<id>/` (distributor session)  
**Role:** DISTRIBUTOR

```
┌─[Nav Shell W-04]──────────────────────────────────────────────────┐
│  ← Dashboard                                                      │
│  Pedido #001                           [Status: DELIVERED]       │
│                                                                   │
│  ORDER ITEMS TABLE (read-only)                                    │
│                                                                   │
│  [Btn: Ver historial de auditoría]  ← Secondary button           │
│                                                                   │
│  AUDIT LOG (expandable or always shown)                           │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ Timestamp    │ Actor        │ Action       │ From → To    │   │
│  │ ──────────── │ ──────────── │ ──────────── │ ──────────── │   │
│  │01/07 14:00   │ Ana (STORE…) │ Pedido creado│ — → PENDING  │   │
│  │01/07 14:10   │ Juan (VENDOR)│ Aceptado     │ PENDING→ACCEPTED│ │
│  │01/07 15:00   │ Juan (VENDOR)│ Despachado   │ ACCEPTED→DISPATCHED│
│  │01/07 16:30   │ Luis (DELIV.)│ Entregado    │ DISPATCHED→DELIVERED│
│  └───────────────────────────────────────────────────────────┘   │
│  (entries are append-only; no delete controls)                    │
└───────────────────────────────────────────────────────────────────┘
```

---

## Appendix: Screen Inventory

| Screen ID | Screen Name | Route (approx.) | Role(s) |
|-----------|-------------|-----------------|---------|
| W-01 | Login | `/accounts/login/` | All |
| W-02 | Password Reset Request | `/accounts/password-reset/` | All |
| W-03 | Set New Password | `/accounts/password-reset/<token>/` | All |
| W-04 | Global Nav Shell | — (shared layout) | All |
| W-05 | Distributor Operations Dashboard | `/distributor/dashboard/` | DISTRIBUTOR |
| W-06 | Product List | `/catalog/products/` | DISTRIBUTOR |
| W-07 | Create / Edit Product | `/catalog/products/new/` etc. | DISTRIBUTOR |
| W-08 | Assign Inventory | `/catalog/inventory/assign/` | DISTRIBUTOR |
| W-09 | User Management | `/accounts/users/` | DISTRIBUTOR |
| W-10 | Vendor Dashboard | `/orders/vendor-dashboard/` | VENDOR |
| W-11 | Order Detail — Vendor | `/orders/<id>/` | VENDOR |
| W-11a | Modal: Accept Order | (inline modal on W-11) | VENDOR |
| W-11b | Modal: Reject Order | (inline modal on W-11) | VENDOR |
| W-12 | Store Owner Dashboard | `/orders/store-dashboard/` | STORE_OWNER |
| W-13 | Place Order — Step 0: Select Store | `/orders/new/` | STORE_OWNER |
| W-14 | Place Order — Step 1: Products | `/orders/new/` | STORE_OWNER |
| W-15 | Place Order — Step 2: Review | `/orders/new/` | STORE_OWNER |
| W-15b | Place Order — Step 3: Confirmation | `/orders/new/` | STORE_OWNER |
| W-16 | Order Detail — Store Owner | `/orders/<id>/` | STORE_OWNER |
| W-17 | Notification Center | `/accounts/notifications/` | STORE_OWNER |
| W-18 | Delivery Queue | `/deliveries/queue/` | DELIVERY |
| W-19 | Delivery Confirmation Form | `/deliveries/<id>/confirm/` | DELIVERY |
| W-20 | Order Detail — Distributor | `/orders/<id>/` | DISTRIBUTOR |

---

## Appendix B: Template & URL Implementation Status

### Implemented (Sprint 1 — Templates + Route Alignment)

| Wireframe | Screen | URL | Template |
|-----------|--------|-----|----------|
| W-04 | Global Nav Shell | — | `templates/base.html` |
| W-09 | User Management | `accounts/users/` | `accounts/index.html` |
| — | Distributor Detail | `accounts/distributors/<id>/` | `accounts/obtener_distribuidor.html` |
| — | Create Distributor | `accounts/distributors/new/` | `accounts/crear_distribuidor.html` |
| — | Edit Distributor | `accounts/distributors/<id>/edit/` | `accounts/editar_distribuidor.html` |
| — | Create User | `accounts/users/new/` | `accounts/crear_usuario.html` |
| — | Edit User | `accounts/users/<id>/edit/` | `accounts/editar_usuario.html` |
| W-06/W-08 | Catalog Overview | `catalog/` | `catalog/index.html` |
| W-07 | Create Product | `catalog/products/new/` | `catalog/crear_producto.html` |
| W-07 | Edit Product | `catalog/products/<id>/edit/` | `catalog/editar_producto.html` |
| — | Create Store | `catalog/stores/new/` | `catalog/crear_tienda.html` |
| — | Edit Store | `catalog/stores/<id>/edit/` | `catalog/editar_tienda.html` |
| W-08 | Assign Inventory | `catalog/inventory/assign/<vendor_id>/` | `catalog/crear_inventario.html` |
| — | Edit Inventory | `catalog/inventory/<id>/edit/` | `catalog/editar_inventario.html` |
| W-05 | Orders List | `orders/` | `orders/index.html` |
| W-11/W-16/W-20 | Order Detail | `orders/<id>/` | `orders/ver_pedido.html` |
| — | Create Order | `orders/new/` | `orders/crear_pedido.html` |
| — | Edit Order | `orders/<id>/edit/` | `orders/editar_pedido.html` |
| — | Add Item | `orders/<order_id>/items/new/` | `orders/crear_item_pedido.html` |
| — | Edit Item | `orders/items/<id>/edit/` | `orders/editar_item_pedido.html` |
| W-18 | Delivery Queue | `deliveries/queue/` | `deliveries/index.html` |
| W-19 | Confirm Delivery | `deliveries/new/confirm/` | `deliveries/crear_confirmacion.html` |
| — | Edit Confirmation | `deliveries/<id>/edit/` | `deliveries/editar_confirmacion.html` |
| W-20 | Audit Log | `audit/` | `audit/index.html` |

### Not Yet Implemented

| Wireframe | Screen | Blocked on |
|-----------|--------|------------|
| W-01 | Login | Django auth setup + login view |
| W-02 | Password Reset Request | SMTP config + PasswordResetToken logic |
| W-03 | Set New Password | Token validation view |
| W-10 | Vendor Dashboard + JS Polling | Auth + role filter + `/api/orders/pending/` endpoint |
| W-11a | Accept Order modal | `POST /orders/<id>/accept/` view + atomic transaction |
| W-11b | Reject Order modal | `POST /orders/<id>/reject/` view |
| W-12 | Store Owner Dashboard | Auth + role-scoped order list |
| W-13–W-15b | Multi-step order wizard | Session-based form wizard + vendor auto-assign |
| W-17 | Notification Center | Notification model + views |
| W-19 (full) | Delivery confirm with Cloudinary | Cloudinary SDK + public_id validation |

---

*End of UX Navigation Flows & Conceptual Wireframes document.*
