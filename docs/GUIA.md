# Guía del proyecto — Pedidos JDG

Aplicación para manejar el ciclo de **pedidos a proveedores** del almacén de
Importadora JDG: del *sugerido* del responsable de tienda al *análisis y
negociación* del administrador, el **cierre** del pedido y la generación de un
**PDF** con lo acordado.

Es un proyecto **separado** del panel de control JDG (`proyecto-jdg`), del que
lee (solo lectura) el catálogo y los datos de cada producto para autocompletar
descripción, costo de la última compra (con IVA) y métricas de rotación.

---

## 1. Cómo correr la app en local

Desde la carpeta del proyecto (`D:\Jupyter_Notebooks\proyecto-pedidos`):

```bash
.venv\Scripts\python.exe -m streamlit run app/app.py --server.port 8502
```

Luego abre **http://localhost:8502**.

> Se usa el puerto **8502** (y no el 8501 por defecto) para no chocar con el
> panel de JDG, que suele estar corriendo en el 8501.

Para detenerla: **Ctrl+C** en la terminal.

### Entorno

- Python 3.12, en un entorno virtual propio dentro de `.venv/`.
- Dependencias en `requirements.txt` (Streamlit, Supabase, pandas, pyarrow, fpdf2).
- Para reinstalar dependencias:
  ```bash
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  ```

---

## 2. Base de datos (Supabase)

Los pedidos se guardan en **Supabase** (base de datos Postgres en la nube +
autenticación de usuarios).

### Credenciales

Viven en `.streamlit/secrets.toml` (**no se sube al repo**, está en `.gitignore`).
La plantilla es `.streamlit/secrets.toml.example`. Contiene:

- `url` — Project URL de Supabase (solo el dominio base, sin `/rest/v1/`).
- `publishable_key` — llave pública (`sb_publishable_…`), para el login.
- `secret_key` — llave privada (`sb_secret_…`), para leer/escribir del lado del
  servidor. **Nunca se expone en el navegador.**

### Esquema (scripts en `db/`)

Se ejecutan una vez en **Supabase → SQL Editor → New query → Run**:

| Archivo | Qué crea |
|---|---|
| `db/001_esquema_inicial.sql` | Tablas `proveedores`, `pedidos`, `pedido_items` + numeración automática y permisos. |
| `db/002_perfiles.sql` | Tabla `perfiles` (correo → rol). |
| `db/003_precio_final.sql` | Columna `precio_final_acordado` en `pedido_items`. |
| `db/004_reset_numeracion.sql` | Reinicia la numeración a `PED-AAAA-0001` (opcional, tras limpiar datos de prueba). |

Los `001`–`003` son idempotentes (se pueden volver a correr sin romper lo
existente); el `004` solo se corre cuando la tabla `pedidos` está vacía.

---

## 3. Modelo de datos

### `proveedores`
Catálogo de proveedores: `nombre`, `ruc`, `dias_credito_habitual`. Al crear un
pedido, la tienda elige de la **lista de proveedores de JDG** (columna
`PROVEEDOR`); el proveedor elegido se guarda en esta tabla la primera vez que se
usa (`obtener_o_crear_proveedor`). También se puede registrar uno nuevo a mano.

### `pedidos` (cabecera)
Un pedido por cita con un proveedor.

| Campo | Significado |
|---|---|
| `numero_pedido` | Identificador legible `PED-AAAA-NNNN`, **se genera solo**. |
| `proveedor_id` | Proveedor del pedido. |
| `fecha_cita` | Fecha de la reunión con el proveedor. |
| `responsable` | Correo del responsable de tienda que hizo el sugerido. |
| `estado` | Etapa del pedido (ver máquina de estados). |
| `dias_credito`, `descuento_pct` | Condiciones acordadas en la negociación. |
| `comentario_admin` | Comentario único del administrador sobre la negociación. |

### `pedido_items` (líneas)
Un producto por fila.

| Campo | Quién lo pone |
|---|---|
| `codigo`, `descripcion` | Tienda (o admin si agrega un producto). |
| `unidades_sugeridas_tienda` | Tienda. |
| `precio_proveedor` | Tienda — oferta inicial del proveedor (con IVA si aplica). |
| `ultimo_precio_compra_sistema` | **Autocompletado desde JDG**: costo de la última compra **con IVA** (`COSTO_ULT_COMPRA_CON_IVA`, dato real de la factura; para exentos iguala al sin IVA). |
| `iva_aplica` | **Autocompletado desde JDG** (`GRAVA_IVA`): si el producto grava IVA. JDG es la autoridad. |
| `observacion_tienda` | Tienda. |
| `unidades_ajustadas_admin` | Admin — cantidad final a pedir. |
| `precio_final_acordado` | Admin — precio de compra negociado. |
| `total` | Se calcula: unidades finales × precio final. |
| `comentario_admin` | Admin — observación por línea. |
| `precio_facturado`, `flag_discrepancia` | Heredadas (la conciliación se movió al sistema de facturación). |

Las métricas de apoyo del administrador (**unidades prom/mes** =
`VENTA_MENSUAL_EN_STOCK`, **días prom. de venta** = `DIAS_ESTANTERIA_VENDIDO`,
FIFO) y la **fecha de última compra** no se guardan: se leen de JDG por código al
mostrar la tabla.

> **Precios como foto.** El `ultimo_precio_compra_sistema` (costo de la última
> compra con IVA) y demás precios se guardan tal cual el día del análisis: el
> pedido es un documento histórico.

---

## 4. Flujo del pedido (máquina de estados)

```
sugerido  →  en_analisis  →  cerrado
                  │
                  └──(devolver)──→ sugerido
```

| Estado | Quién actúa | Qué pasa |
|---|---|---|
| **sugerido** | Responsable de tienda | Registra productos y unidades sugeridas. Al teclear el código, la descripción y el costo de la última compra se completan desde JDG. |
| **en_analisis** | Administrador | Ajusta unidades, cierra el precio final, agrega productos, comenta por línea y fija condiciones. La tabla muestra métricas de JDG (unidades prom/mes y días prom. de venta). |
| **cerrado** | Administrador | Cierra el pedido y descarga el **PDF** con lo acordado. |

No hay conciliación de factura en la app: se hace en el sistema de facturación
(la factura entra automática ahí, sin retecleo). Los estados `enviado` y
`facturado` quedaron como *heredados* (pedidos viejos), fuera del flujo actual.

Los estados válidos y las transiciones están en `src/pedidos/modelo.py`. La base
de datos también restringe los valores posibles (CHECK).

### Roles
- **Responsable de tienda** (`rol = tienda`): crea el pedido y el sugerido.
- **Administrador** (`rol = administrador`): analiza, negocia, cierra y genera el PDF.

El login usa Supabase Auth; el rol se lee de la tabla `perfiles`.

---

## 5. Mapa de código

```
app/app.py                 arranque, login y ruteo por rol
src/pedidos/
  db.py                    conexión a Supabase (secret + publishable)
  auth.py                  login y roles (Supabase Auth + perfiles)
  modelo.py                estados del pedido y transiciones
  repositorio.py           TODA la lectura/escritura a la base
  jdg.py                   lee los parquets de JDG (autocompletado y métricas)
  pdf.py                   genera el PDF del pedido cerrado
  util.py                  utilidades (txt, num)
  vista_tienda.py          vista del responsable de tienda
  vista_admin.py           vista del administrador
  vista_tablero.py         búsqueda y detalle de pedidos
db/*.sql                   esquema de la base (se corre en Supabase)
scripts/                   utilidades de línea de comando (ver abajo)
```

Regla de diseño: **las vistas nunca hablan con Supabase directamente**; todo
pasa por `repositorio.py`.

---

## 6. Scripts de línea de comando

Se corren con `.venv\Scripts\python.exe scripts\<archivo>`:

| Script | Para qué |
|---|---|
| `crear_usuario.py` | Crea un usuario (cuenta + rol). Lo corre el administrador, una vez por persona; pide la contraseña de forma oculta. |
| `sincronizar_jdg.py` | Copia `summary.parquet` y `rendimiento.parquet` del panel JDG a `data/` (para el autocompletado). Versión manual del futuro Action. |
| `probar_conexion.py` | Verifica que la app se conecta a Supabase. |
| `probar_tablas.py` | Verifica que las tablas existen y responden. |

---

## 7. Estado del proyecto

- ✅ **Fase 1 — Esqueleto.** Conexión a Supabase, tablas, login con roles.
- ✅ **Fase 2 — Flujo.** Vista de tienda (sugerido) y de administrador
  (análisis, negociación de precio final, productos agregados, condiciones,
  total en vivo, envío).
- ✅ **Fase 3 — Autocompletado desde JDG.** Al teclear un código se llenan
  descripción, último precio de compra (con IVA) y la casilla de IVA; y un panel
  de apoyo muestra rotación, antigüedad, GMROI y acción. Los datos vienen de
  `data/summary.parquet` (se traen con `scripts/sincronizar_jdg.py`).
- ✅ **Fase 4 — Cierre + tablero.** El administrador cierra el pedido (con
  confirmación) y descarga el **PDF** con lo acordado. Tablero con búsqueda por
  número/estado/proveedor (ambos roles) y detalle del pedido a ancho completo.
  *La conciliación de factura se movió al sistema de facturación, así que se
  eliminó de la app; los estados `enviado`/`facturado` quedan como heredados.*
- ✅ **Fase 5 — Despliegue + sincronización con JDG.** Repo privado en GitHub,
  desplegado en Streamlit Cloud (Python 3.12), y la GitHub Action del día 3 que
  trae los parquets de JDG (probada, en verde). Detalle y mantenimiento en
  `docs/DESPLIEGUE.md`.
- ✅ **Ajustes de uso.** Buscador de producto por código o descripción (bajo una
  casilla, para no ralentizar el tecleo), autocompletado en vivo, logo de JDG en
  la barra lateral, y **conexión endurecida** (HTTP/1.1 + reintentos) para evitar
  el `RemoteProtocolError` intermitente de Supabase.

> ⏰ **Mantenimiento:** el token `JDG_SYNC_TOKEN` de la Action **vence el 5 de
> noviembre de 2026** — renovarlo antes (pasos en `docs/DESPLIEGUE.md`).

---

## 8. Notas y limitaciones conocidas

- La numeración de pedidos no recicla números: cada creación consume un
  correlativo. Para empezar en `PED-AAAA-0001` tras limpiar datos de prueba,
  correr `db/004_reset_numeracion.sql`.
- Si el administrador **devuelve** un pedido a tienda y tienda lo **vuelve a
  guardar**, se pierden los ajustes previos del administrador (el editor de
  tienda no muestra esas columnas). Aceptable por ahora.
- **Pendiente:** diseño para tablet/teléfono (hoy pensada para escritorio) y
  restringir la audiencia de la app (Streamlit → Settings → Sharing), ya que
  muestra costos y márgenes.
