-- =====================================================================
-- Perfiles de usuario — Pedidos JDG (Fase 1.5)
-- Autenticación la maneja Supabase Auth; esta tabla guarda el ROL.
-- Ejecutar en Supabase -> SQL Editor -> New query -> pegar -> Run.
-- =====================================================================

create table if not exists perfiles (
  id         bigint generated always as identity primary key,
  email      text unique not null,
  nombre     text,
  rol        text not null check (rol in ('administrador','tienda')),
  creado_en  timestamptz not null default now()
);

-- La app entra con la secret key (rol service_role); le damos acceso.
grant usage on schema public to service_role;
grant all on all tables in schema public to service_role;
grant all on all sequences in schema public to service_role;
notify pgrst, 'reload schema';
