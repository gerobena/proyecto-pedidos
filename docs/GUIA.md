# Guía del proyecto — Pedidos JDG

Aplicación para manejar el ciclo de **pedidos a proveedores** del almacén de
Importadora JDG: del *sugerido* del responsable de tienda al *análisis* y
*negociación* del administrador, el *envío* al proveedor y (más adelante) la
*conciliación* con la factura de compra.

Es un proyecto **separado** del panel de control JDG (`proyecto-jdg`). En el
futuro leerá los datos de ese panel para autocompletar información de cada
producto (último precio, rotación, rendimiento).

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
- Dependencias en `requirements.txt` (Streamlit, Supabase, pandas, pyarrow).
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

Son idempotentes (se pueden volver a correr sin romper lo existente).

---

## 3. Modelo de datos

### `proveedores`
Catálogo de proveedores: `nombre`, `ruc`, `dias_credito_habitual`.

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
| `ultimo_precio_compra_sistema` | Sistema/JDG (por ahora manual; Fase 3 lo autocompleta). |
| `iva_aplica` | Si el producto grava IVA. |
| `observacion_tienda` | Tienda. |
| `unidades_ajustadas_admin` | Admin — cantidad final a pedir. |
| `precio_final_acordado` | Admin — precio de compra negociado. |
| `total` | Se calcula: unidades finales × precio final. |
| `precio_facturado`, `flag_discrepancia` | Admin — conciliación con la factura (Fase 4). |

> **Precios como foto.** El `ultimo_precio_compra_sistema` y demás precios se
> guardan tal cual el día del análisis. El pedido es un documento histórico: la
> conciliación futura compara contra el precio del día, no contra el precio
> actual del sistema.

---

## 4. Flujo del pedido (máquina de estados)

```
sugerido  →  en_analisis  →  enviado  →  facturado  →  cerrado
                  │
                  └──(devolver)──→ sugerido
```

| Estado | Quién actúa | Qué pasa |
|---|---|---|
| **sugerido** | Responsable de tienda | Registra los productos y unidades sugeridas. |
| **en_analisis** | Administrador | Ajusta unidades, negocia precio final, agrega productos, fija condiciones. |
| **enviado** | Administrador | El pedido se confirmó al proveedor. |
| **facturado** | Administrador | Llegó la factura (Fase 4). |
| **cerrado** | — | Conciliado. |

Los estados válidos y las transiciones están en `src/pedidos/modelo.py`. La base
de datos también restringe los valores posibles (CHECK).

### Roles
- **Responsable de tienda** (`rol = tienda`): crea el pedido y el sugerido.
- **Administrador** (`rol = administrador`): analiza, negocia y envía.

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
  util.py                  utilidades (txt, num)
  vista_tienda.py          vista del responsable de tienda
  vista_admin.py           vista del administrador
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
| `probar_conexion.py` | Verifica que la app se conecta a Supabase. |
| `probar_tablas.py` | Verifica que las tablas existen y responden. |
| `probar_repositorio.py` | Prueba de humo: crea un pedido con ítems y lo borra. |
| `probar_flujo_admin.py` | Prueba el flujo tienda → análisis → enviado. |
| `probar_negociacion.py` | Prueba ajuste de precio final + producto agregado. |

Los scripts `probar_*` crean datos de prueba y **los borran al final**.

---

## 7. Estado del proyecto

- ✅ **Fase 1 — Esqueleto.** Conexión a Supabase, tablas, login con roles.
- ✅ **Fase 2 — Flujo.** Vista de tienda (sugerido) y de administrador
  (análisis, negociación de precio final, productos agregados, condiciones,
  total en vivo, envío).
- ⬜ **Fase 3 — Autocompletado desde JDG.** Al teclear un código, traer último
  precio de compra, rotación y rendimiento del panel JDG.
- ⬜ **Fase 4 — Conciliación.** Cargar el precio facturado y compararlo con el
  precio final acordado; tablero y búsqueda por número de pedido.
- ⬜ **Fase 5 — Sincronización con JDG.** GitHub Action programada (día 3) que
  copia los parquets de JDG al proyecto de pedidos. *Último paso.*

---

## 8. Notas y limitaciones conocidas

- La numeración de pedidos no recicla números: cada creación (incluidas las
  pruebas) consume un correlativo. Es normal.
- Si el administrador **devuelve** un pedido a tienda y tienda lo **vuelve a
  guardar**, se pierden los ajustes previos del administrador (el editor de
  tienda no muestra esas columnas). Aceptable por ahora; a revisar si molesta.
- La app aún es abierta por URL local. Antes de desplegarla habrá que restringir
  la audiencia (lleva costos y márgenes).
