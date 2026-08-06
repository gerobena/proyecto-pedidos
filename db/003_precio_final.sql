-- =====================================================================
-- Precio final acordado — Pedidos JDG (Fase 2)
-- El administrador negocia y cierra un precio de compra final, distinto de
-- la oferta inicial (precio_proveedor) que registró tienda.
-- Ejecutar en Supabase -> SQL Editor -> New query -> pegar -> Run.
-- =====================================================================

alter table pedido_items
  add column if not exists precio_final_acordado numeric;

-- Recarga el esquema para que la API vea la columna nueva.
notify pgrst, 'reload schema';
