# TODOS — proyecto-distribuidora

Task backlog derived from the gap analysis in `docs/requirements.md`'s "Implementation
Status & Known Issues" section. Ordered by priority; Tier 1 blocks everything after it.
Update checkboxes as items land; don't reorder history, append new items at the end of
their tier.

## Sprint 1 addendum — Account provisioning redesign (DR-08) — DONE 2026-07-16

Not in the original Tier 1 scope — added after testing surfaced two real gaps: creating
a Distributor was a two-step superuser+/admin/ flow, and STORE_OWNER accounts had no
self-service path despite that role being the least technical.

- [x] `Distributor.invite_token` field + `regenerate_invite_token()` (migration
      `0004_distributor_invite_token.py`, backfilled for existing rows).
- [x] Combined superuser onboarding: `crear_distribuidor` now creates the `Distributor`
      + its first `DISTRIBUTOR` user atomically (`DistributorOnboardingForm`).
- [x] Store-owner self-registration via per-distributor invite link:
      `accounts/join/<token>/` (`registrar_tienda`), no public distributor picker,
      auto-login on success, new store starts with no vendor assigned (existing DR-01
      message covers it).
- [x] Invite link shown + regenerable from the distributor's own dashboard
      (`accounts/index.html`).
- [x] Fixed a pre-existing broken-link bug found along the way: the superuser-only
      Distributor templates linked "Volver"/"Cancelar" to `index_accounts`, which is
      `role_required('DISTRIBUTOR')` — a plain superuser (no `role`) got 403 clicking
      them. Now point to `admin:index`.
- Documented as DR-08 in `docs/requirements.md`. Verified via `manage.py check` and a
  test-client smoke test (combined onboarding, join-link happy path, bogus token 404,
  regenerate invalidates the old token).
- **Known gap, not closed:** no rate-limiting/CAPTCHA on the join endpoint, no email
  verification for self-registered store owners.

## Tier 1 — Foundational (Sprint 1, blocks everything else) — DONE 2026-07-16

- [x] Consolidate the two `base.html` files — merged into
      `proyectoDistribuidora/templates/base.html` (the one in `TEMPLATES[0]['DIRS']`);
      the shadowed `catalog/templates/base.html` copy was removed.
- [x] `accounts/decorators.py` — `role_required(*roles)` and `superuser_required` added.
- [x] RBAC applied everywhere — `accounts`, `catalog`, `orders`, `deliveries`, `audit`
      views all decorated; `catalog` upgraded from bare `@login_required`.
- [x] Tenant isolation applied — every queryset scoped by `distributor` (directly or via
      `vendor__distributor`/`store__distributor`/`order__store__distributor`), including
      the DRF catalog viewsets (`get_queryset` + `perform_create` distributor stamping +
      cross-tenant FK validation on `owner`/`vendor`/`product`). Also closed two
      tenant-leak holes found along the way: `distributor` was a raw client-editable
      field on `StoreForm`/`ProductForm`/`UserCreateForm` — removed, now stamped
      server-side; `DeliveryConfirmationForm` let the caller set `delivery_user` to
      anyone — removed, now set from `request.user`.
- [x] Password reset flow — `solicitar_reset_password`/`confirmar_reset_password` views,
      forms, templates, and URLs added; `EMAIL_BACKEND` set to console for local dev.
- [x] `Distributor` CRUD scoped to `@superuser_required`; `accounts/index` split from a
      loop-over-all-distributors view into a single-tenant user-management page.
- Verified via `manage.py check`, `makemigrations --check`, and a Django test-client
  smoke test (role block, tenant isolation, superuser gate, anonymous redirect,
  password-reset token issuance) — all passed.

## Tier 2 — Order lifecycle correctness (Sprint 3) — DONE 2026-07-16

- [x] Fix price/state integrity bugs: `OrderForm` now only exposes `store`;
      `OrderItemForm` drops `unit_price_at_time` (server-snapshot from
      `Product.unit_price` on create and edit). Bonus: `product` choices scoped to the
      order's vendor's inventory (FR-05.3), closing that gap as a side effect.
- [x] Dedicated `aceptar_pedido`/`rechazar_pedido`/`despachar_pedido` views —
      `transaction.atomic()` + `select_for_update()` on `VendorInventory`, per-item
      insufficient-stock errors, order stays `PENDING` on failure. Replaced the old
      generic `editar_pedido`/`eliminar_pedido` (removed — they let status be set
      directly, bypassing the state machine).
- [x] Added `cancelar_pedido` (STORE_OWNER, PENDING-only) — wasn't in the original Tier 2
      list, but needed once the generic edit/delete views were removed; implements
      US-23 early (was slated for Tier 4).
- [x] `GET /api/orders/pending/` (root `urls.py`) — vendor-scoped JSON endpoint, distinct
      from the catalog DRF API. 30s JS polling on `orders/index.html` prepends new
      `PENDING` orders without a reload (FR-06.6, FR-10.1, US-10).
- [x] Store-owner order status view (FR-05.5) — satisfied by the existing role-scoped
      `index`/`ver_pedido` views once status display was cleaned up; no separate page
      needed.
- Documented as a resolved section in `docs/requirements.md`'s Implementation Status.
  Verified via `manage.py check` and a test-client smoke test: full lifecycle
  (create → accept w/ stock deduction → dispatch), insufficient-stock rollback,
  reject-with-reason, cancel, and the polling endpoint.
- **Not done, still open:** `AuditLog` writes on transitions and in-app notifications on
  transition are Tier 3/4 as originally planned — accept/reject/dispatch/cancel don't
  write audit entries or notify the store owner yet.

## Sprint addendum — Delivery confirmation redesign (DR-09) — DONE 2026-07-18

Not in the original Tier 3 scope — replaces the Cloudinary item below entirely, not
just the SDK piece. Store-owner attestation replaces photo proof as the source of
truth for delivery correctness.

- [x] `Order.status` gains `DELIVERY_ISSUE` / `CONFIRMED`; `DELIVERED` is now
      non-terminal (migration `orders/0003_order_issue_description_...`).
- [x] `deliveries.crear_confirmacion` now transitions `Order` to `DELIVERED` and
      notifies the store owner — closed a pre-existing gap where this view never
      touched `Order.status` at all. `DeliveryConfirmationForm`'s `order` field is
      now scoped to `DISPATCHED` orders only.
- [x] `DeliveryConfirmation.photo_public_id` made optional (`blank=True`), never
      validated — no Cloudinary dependency.
- [x] New `orders/` views: `confirmar_recepcion`, `reportar_incidencia`,
      `resolver_incidencia` — see DR-09 in `docs/requirements.md` for the full flow.
- [x] `AuditLog` writes on `order_confirmed` / `delivery_issue_resolved` (scoped to
      just these two new transitions, not a general audit-writing pass).
- [x] `Notification` writes on delivered / issue-reported / issue-resolved /
      confirmed (first real use of the `Notification` model — Tier 4's "wire
      creation on every order transition" is still open for the older
      accept/reject/dispatch transitions).
- Verified via `manage.py migrate` + a Django test-client smoke test covering both
  paths (happy-path confirm, and report-issue → resolve-issue) plus a 404 guard-rail
  check (vendor can't resolve an order that isn't in `DELIVERY_ISSUE`).
- **Known gap, not closed:** issue resolution is notes-only — no inventory
  adjustment, partial fulfillment, or redelivery tracking (see Tier 4).

## Tier 3 — Delivery, audit, dashboard (Sprints 2 & 4) — DONE 2026-07-19

- [x] ~~Cloudinary upload preset + server-side `public_id` validation~~ —
      **superseded by DR-09**, not implemented: photo proof is dropped from scope
      entirely, not just the Cloudinary SDK piece.
- [x] `AuditLog` writes backfilled onto `aceptar_pedido` (+ per-item deduction detail
      and an `order_accept_failed` entry on insufficient stock, FR-09.3),
      `rechazar_pedido`, `despachar_pedido`, `cancelar_pedido`, and
      `deliveries.crear_confirmacion`'s `DELIVERED` transition. Every order status
      transition now has an audit entry, matching the DR-09 transitions that already
      had one.
- [x] Distributor operations dashboard (`accounts/dashboard.html`,
      `/accounts/dashboard/`) — orders grouped by status, 20 most recent orders,
      inventory per product per vendor with a low-stock row highlight (FR-08.1,
      FR-08.3). Linked from the nav for `DISTRIBUTOR` users only.
- [x] `Order` gained a composite index on `(vendor, status)` and one on `store`
      (NFR-02.6, migration `orders/0004_...`). Fixed N+1s (NFR-02.5) across every
      list view that joins related data: `orders/` index/detail (store, vendor),
      `pending_orders_api` (item count was one `COUNT` query per order, now a single
      `annotate`), `catalog/index.html` (store/product/inventory joins),
      `deliveries/index.html` (order, delivery_user), `audit/index.html` (user).
- Bonus fix found along the way: `deliveries/index.html`'s "Foto ID (Cloudinary)"
  column header was stale after DR-09 — relabeled "Foto ID (opcional, sin validar)".
- Verified via `manage.py check`, `makemigrations --check`, and `manage.py migrate`.

## Tier 4 — Secondary features (Sprint 5) — DONE 2026-07-19

- [x] Notifications — writes added on `aceptar_pedido`/`rechazar_pedido`/
      `despachar_pedido` (the DR-09 transitions and `deliveries.crear_confirmacion`
      already had them; `cancelar_pedido` deliberately doesn't notify — it's the
      store owner's own action, no FR-10 sub-item covers it). Unread count via a new
      `accounts.context_processors.notifications` context processor, shown in the nav
      for any authenticated role (not just `STORE_OWNER` — `VENDOR`/`DELIVERY` get
      DR-09 notifications too). New `/accounts/notifications/` list page with
      mark-as-read / mark-all-read.
- [x] Dashboard filters (date range, vendor, store, status) + summary metrics (total,
      fulfilled = `CONFIRMED`, rejected, avg fulfillment time) — all on
      `/accounts/dashboard/` via GET params, filters apply to both the order list and
      the metrics.
- [x] Low-stock alert badge — summary banner on the dashboard + the existing
      per-row highlight, now with the same ⚠ text marker `catalog/index.html`
      already had (the dashboard's inventory table only had the CSS highlight
      before this pass).
- Verified via `manage.py check` and a test-client smoke test: notification created +
  correct message on accept, unread count shown in the nav, notifications list page,
  mark-as-read flips `is_read`, dashboard filters (vendor/status combos) correctly
  include/exclude orders, low-stock banner appears once inventory drops below
  threshold.

## Tier 5 — Hardening & ship (Sprint 6)

- [ ] Unit tests: order state transitions, price-snapshot logic, password reset token
      expiry/single-use.
- [ ] Integration tests: atomic accept race condition (concurrent accepts, exactly one
      succeeds), rollback leaves order+inventory unchanged, tenant isolation
      (Distributor A can't read Distributor B's data).
- [ ] Playwright e2e: the 4 critical paths (place order → accept → dispatch → deliver;
      distributor dashboard view) + the error path + the security/RBAC path.
- [ ] Production deploy config: WhiteNoise, `dj-database-url`, Procfile/Gunicorn, real
      Cloudinary/Resend credentials via environment variables.

## Cross-cutting / housekeeping

- [x] Tenant/role-scope the DRF catalog API (`catalog/api_views.py`) — done as part of
      Tier 1 (see above): `IsDistributor` permission + tenant-scoped `get_queryset` +
      cross-tenant FK rejection on create.
- [ ] Decide on the committed `proyectoDistribuidora.zip` at the repo root — very
      likely an accidental commit, not evaluated further here.
- [ ] Either actually adopt Tailwind or drop the claim — current CSS
      (`static/css/styles.css`) is hand-written, not Tailwind, despite an earlier commit
      message claiming otherwise.
