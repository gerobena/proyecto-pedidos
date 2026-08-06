# Proyecto Pedidos JDG

Aplicación para manejar el ciclo de **pedidos a proveedores** del almacén de
Importadora JDG: del **sugerido** del responsable de tienda al **análisis y
negociación** del administrador, el **envío** al proveedor y la **conciliación**
con la factura de compra.

App **separada** del panel de control JDG (`proyecto-jdg`). En el futuro leerá en
solo lectura los datos del panel (último precio de compra, rotación, rendimiento)
para autocompletar los ítems del sugerido.

## Stack

- **Streamlit** — interfaz (Python).
- **Supabase** — base de datos Postgres hospedada + autenticación de usuarios.

## Cómo correr

```bash
.venv\Scripts\python.exe -m streamlit run app/app.py --server.port 8502
```

Abre **http://localhost:8502**. (Puerto 8502 para no chocar con el panel JDG en
el 8501.)

## Estructura

```
app/app.py            arranque, login y ruteo por rol
src/pedidos/
  db.py               conexión a Supabase
  auth.py             login y roles
  modelo.py           estados del pedido y transiciones
  repositorio.py      toda la lectura/escritura a la base
  util.py             utilidades
  vista_tienda.py     vista del responsable de tienda
  vista_admin.py      vista del administrador
db/*.sql              esquema de la base (se corre en Supabase)
scripts/              utilidades y pruebas de línea de comando
docs/GUIA.md          documentación completa
data/                 catálogo y parquets de JDG sincronizados (no se versionan)
.streamlit/secrets.toml   credenciales de Supabase (NO se sube al repo)
```

## Estado

- ✅ **Fase 1 — Esqueleto** (conexión, tablas, login con roles).
- ✅ **Fase 2 — Flujo** (sugerido de tienda + análisis/negociación del admin).
- ⬜ **Fase 3 — Autocompletado desde JDG.**
- ⬜ **Fase 4 — Conciliación de factura + tablero/búsqueda.**
- ⬜ **Fase 5 — Sincronización con JDG** (GitHub Action, día 3). *Último paso.*

**La documentación completa está en [`docs/GUIA.md`](docs/GUIA.md)** (modelo de
datos, flujo, scripts, cómo configurar Supabase).
