-- =====================================================================
-- Esquema inicial — Pedidos JDG (Fase 1)
-- Ejecutar en Supabase -> SQL Editor -> New query -> pegar todo -> Run.
-- Es idempotente: se puede volver a correr sin romper lo ya creado.
-- =====================================================================

-- Función util: mantiene "actualizado_en" al día en cada UPDATE.
create or replace function set_actualizado_en()
returns trigger
language plpgsql
as $$
begin
  new.actualizado_en := now();
  return new;
end;
$$;

-- =====================================================================
-- 1) PROVEEDORES
-- =====================================================================
create table if not exists proveedores (
  id                     bigint generated always as identity primary key,
  nombre                 text not null,
  ruc                    text,
  dias_credito_habitual  integer,
  creado_en              timestamptz not null default now()
);

-- =====================================================================
-- 2) PEDIDOS (cabecera)
-- =====================================================================
create table if not exists pedidos (
  id               bigint generated always as identity primary key,
  numero_pedido    text unique,                    -- PED-2026-0001 (lo pone el trigger)
  proveedor_id     bigint references proveedores(id),
  fecha_cita       date,
  responsable      text,                           -- quien hizo el sugerido
  administrador    text,                           -- quien analizó
  estado           text not null default 'sugerido'
                   check (estado in ('sugerido','en_analisis','enviado','facturado','cerrado')),
  dias_credito     integer,                        -- acordado en este pedido
  descuento_pct    numeric,                        -- acordado en este pedido
  comentario_admin text,
  creado_en        timestamptz not null default now(),
  actualizado_en   timestamptz not null default now()
);

-- Numeración automática y segura ante concurrencia: PED-<año>-<correlativo>.
create sequence if not exists pedidos_folio_seq;

create or replace function set_numero_pedido()
returns trigger
language plpgsql
as $$
begin
  if new.numero_pedido is null then
    new.numero_pedido := 'PED-' || to_char(now(), 'YYYY') || '-' ||
                         lpad(nextval('pedidos_folio_seq')::text, 4, '0');
  end if;
  return new;
end;
$$;

drop trigger if exists trg_numero_pedido on pedidos;
create trigger trg_numero_pedido
before insert on pedidos
for each row execute function set_numero_pedido();

drop trigger if exists trg_pedidos_actualizado on pedidos;
create trigger trg_pedidos_actualizado
before update on pedidos
for each row execute function set_actualizado_en();

-- =====================================================================
-- 3) PEDIDO_ITEMS (líneas del pedido)
-- =====================================================================
create table if not exists pedido_items (
  id                            bigint generated always as identity primary key,
  pedido_id                     bigint not null references pedidos(id) on delete cascade,
  codigo                        text,
  descripcion                   text,
  -- unidades: se guardan las dos versiones para ver el ajuste del admin
  unidades_sugeridas_tienda     numeric,
  unidades_ajustadas_admin      numeric,
  -- precios (CON IVA cuando el producto grava IVA); son una foto del momento
  ultimo_precio_compra_sistema  numeric,
  precio_proveedor              numeric,
  iva_aplica                    boolean not null default true,
  total                         numeric,
  observacion_tienda            text,
  comentario_admin              text,
  -- conciliación con la factura de compra (Fase 4)
  precio_facturado              numeric,
  flag_discrepancia             boolean not null default false,
  creado_en                     timestamptz not null default now()
);

create index if not exists idx_pedido_items_pedido on pedido_items(pedido_id);
create index if not exists idx_pedido_items_codigo on pedido_items(codigo);

-- =====================================================================
-- 4) Permisos: la app entra con la secret key (rol service_role).
--    Le damos acceso de lectura/escritura; el público (anon) queda fuera.
-- =====================================================================
grant usage on schema public to service_role;
grant all on all tables in schema public to service_role;
grant all on all sequences in schema public to service_role;
notify pgrst, 'reload schema';

-- =====================================================================
-- 5) Semilla opcional: un proveedor de ejemplo para poder probar.
--    Bórralo luego con: delete from proveedores where nombre = 'Proveedor de Ejemplo';
-- =====================================================================
insert into proveedores (nombre, ruc, dias_credito_habitual)
select 'Proveedor de Ejemplo', '9999999999001', 30
where not exists (select 1 from proveedores where nombre = 'Proveedor de Ejemplo');
