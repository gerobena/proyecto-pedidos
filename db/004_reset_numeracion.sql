-- =====================================================================
-- Reinicia la numeración de pedidos para empezar en PED-AAAA-0001.
-- Correr UNA sola vez, en Supabase -> SQL Editor, tras limpiar los datos
-- de prueba (cuando la tabla `pedidos` está vacía).
-- =====================================================================

alter sequence pedidos_folio_seq restart with 1;
