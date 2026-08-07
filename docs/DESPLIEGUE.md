# Despliegue — Pedidos JDG

Cómo poner la app en línea y mantener sus datos al día. Tres piezas:

1. **Repo privado** en GitHub.
2. **Streamlit Cloud** sirve la app (Python 3.12 + secrets de Supabase).
3. **GitHub Action** (día 3) sincroniza los parquets de JDG.

> ⚠️ El repo debe ser **privado**: `data/summary.parquet` lleva costos y
> márgenes, y la app muestra precios de compra. Además, el acceso a la app queda
> detrás del login (Supabase Auth).

---

## 1. Subir el repo a GitHub (privado)

1. Crea un repositorio **privado** en GitHub, por ejemplo `gerobena/proyecto-pedidos`
   (sin README ni .gitignore; el repo local ya los tiene).
2. Desde la carpeta del proyecto, conecta y sube:
   ```bash
   git remote add origin https://github.com/gerobena/proyecto-pedidos.git
   git push -u origin master
   ```

Qué NO se sube (protegido por `.gitignore`): `.streamlit/secrets.toml`, `.venv/`.
Qué SÍ se sube: el código, y los parquets `data/summary.parquet` y
`data/rendimiento.parquet` (los necesita la app desplegada).

---

## 2. Desplegar en Streamlit Cloud

1. Entra a https://share.streamlit.io con tu cuenta de GitHub.
2. **New app** → elige el repo `proyecto-pedidos`, rama `master`, y como
   **Main file path**: `app/app.py`.
3. En **Advanced settings**:
   - **Python version: 3.12** (importante; por defecto usa una más nueva y las
     dependencias pueden no compilar).
   - **Secrets**: pega el contenido de tu `.streamlit/secrets.toml` local:
     ```toml
     [supabase]
     url = "https://TU-PROYECTO.supabase.co"
     publishable_key = "sb_publishable_..."
     secret_key = "sb_secret_..."
     ```
4. **Deploy**. La primera vez tarda un par de minutos.
5. (Recomendado) Restringe la audiencia: **Settings → Sharing → Only specific
   people**, y agrega los correos autorizados. Aunque el login ya protege el
   contenido, esto añade una capa.

---

## 3. GitHub Action: sincronizar parquets de JDG

La Action `.github/workflows/sincronizar_jdg.yml` corre el **día 3 de cada mes**
(un día después del ETL de JDG), toma `summary.parquet` y `rendimiento.parquet`
del repo de JDG, los copia a `data/` y los commitea. Ese commit hace que
Streamlit Cloud redesplegue con los datos frescos.

Para que pueda leer el repo **privado** de JDG necesita un token:

### Crear el token (una vez)

1. En GitHub: **Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token**.
2. Configúralo así:
   - **Resource owner:** tu cuenta (`gerobena`).
   - **Repository access:** *Only select repositories* → `proyecto-jdg`.
   - **Permissions → Repository permissions → Contents: Read-only**.
   - **Expiration:** lo que prefieras (recuerda renovarlo cuando venza).
3. Genera y **copia el token** (se muestra una sola vez).

### Guardar el token como secret del repo de pedidos

1. En el repo `proyecto-pedidos`: **Settings → Secrets and variables → Actions →
   New repository secret**.
2. **Name:** `JDG_SYNC_TOKEN` — **Secret:** pega el token. Guarda.

### Probar la Action

1. En el repo de pedidos, pestaña **Actions** → *Sincronizar parquets de JDG* →
   **Run workflow** (ejecución manual).
2. Si todo está bien, verás un commit `chore: sincroniza parquets de JDG (...)`
   cuando haya cambios, y Streamlit redesplegará.

> La Action también corre sola cada día 3. Si algún mes JDG no cambió, no
> commitea nada (es idempotente).

---

## Sincronización manual en local

Para actualizar los parquets en tu máquina (desarrollo), sin esperar a la Action:

```bash
.venv\Scripts\python.exe scripts\sincronizar_jdg.py
```

Copia los parquets desde `D:/Jupyter_Notebooks/proyecto-jdg/data`.

---

## Resumen de secretos

| Dónde | Secreto | Para qué |
|---|---|---|
| Streamlit Cloud (app settings) | `[supabase]` url / publishable_key / secret_key | Conexión a la base |
| GitHub repo `proyecto-pedidos` (Actions secret) | `JDG_SYNC_TOKEN` | Leer los parquets del repo de JDG |
| Local | `.streamlit/secrets.toml` | Desarrollo (no se sube) |
