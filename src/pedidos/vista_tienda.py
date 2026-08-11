"""Vista del Responsable de tienda: crear el pedido y registrar el sugerido."""
from __future__ import annotations

import math
from datetime import date

import pandas as pd
import streamlit as st

from . import jdg
from . import modelo
from . import repositorio as repo
from . import ui
from . import vista_tablero
from .util import iguales

# Orden de columnas: costo última compra y precio proveedor juntos para
# compararlos de un vistazo. Sin columna de IVA (todo va con IVA si aplica).
COLUMNAS_ITEMS = [
    "codigo",
    "descripcion",
    "fecha_ult_compra",
    "ultimo_precio_compra_sistema",
    "precio_proveedor",
    "unidades_sugeridas_tienda",
    "observacion_tienda",
]

CONFIG_COLUMNAS = {
    "codigo": st.column_config.TextColumn("Código"),
    "descripcion": st.column_config.TextColumn("Descripción", width="large"),
    "fecha_ult_compra": st.column_config.TextColumn("Fecha últ. compra"),
    "ultimo_precio_compra_sistema": st.column_config.NumberColumn(
        "Costo última compra", help="De JDG, con IVA si aplica", format="%.2f"
    ),
    "precio_proveedor": st.column_config.NumberColumn(
        "Precio proveedor", help="Con IVA si aplica", format="%.2f"
    ),
    "unidades_sugeridas_tienda": st.column_config.NumberColumn(
        "Unid. sugeridas", min_value=0, step=1
    ),
    "observacion_tienda": st.column_config.TextColumn("Observación", width="large"),
}

# Columnas que trae JDG (no editables por la tienda).
COLS_LECTURA = ["fecha_ult_compra", "ultimo_precio_compra_sistema"]


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def _txt(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _num(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _mapa_proveedores() -> dict[int, str]:
    return {p["id"]: p["nombre"] for p in repo.listar_proveedores()}


def _enriquecer(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    """Trae de JDG descripción, costo y fecha del código de cada fila.

    Sobreescribe si el código cambió (así al cambiar el código se actualizan los
    datos). No toca filas cuyo código no está en JDG (datos escritos a mano).
    """
    df = df.copy()
    cambio = False
    for idx, r in df.iterrows():
        cod = _txt(r.get("codigo"))
        if not cod:
            continue
        info = jdg.info(cod)
        if not info:
            continue
        desc_j = info.get("descripcion")
        if desc_j and _txt(r.get("descripcion")) != desc_j:
            df.at[idx, "descripcion"] = desc_j
            cambio = True
        costo_j = info.get("ultimo_precio_con_iva")
        if costo_j is not None and not iguales(
            _num(r.get("ultimo_precio_compra_sistema")), costo_j
        ):
            df.at[idx, "ultimo_precio_compra_sistema"] = costo_j
            cambio = True
        fecha = info.get("fecha_ult_compra")
        fecha_j = str(fecha)[:10] if fecha is not None else None
        if fecha_j and _txt(r.get("fecha_ult_compra")) != fecha_j:
            df.at[idx, "fecha_ult_compra"] = fecha_j
            cambio = True
    return df, cambio


def _df_items(pedido_id: int) -> pd.DataFrame:
    items = repo.listar_items(pedido_id)
    df = pd.DataFrame(items) if items else pd.DataFrame([{}])
    for c in COLUMNAS_ITEMS:
        if c not in df.columns:
            df[c] = None
    df, _ = _enriquecer(df[COLUMNAS_ITEMS])
    return df


def _guardar_items(pedido_id: int, df: pd.DataFrame) -> int:
    filas: list[dict] = []
    for _, r in df.iterrows():
        codigo = _txt(r.get("codigo"))
        descripcion = _txt(r.get("descripcion"))
        if not codigo and not descripcion:
            continue
        unidades = _num(r.get("unidades_sugeridas_tienda"))
        precio_prov = _num(r.get("precio_proveedor"))
        total = round(unidades * precio_prov, 2) if unidades and precio_prov else None
        ultimo_precio = _num(r.get("ultimo_precio_compra_sistema"))
        descripcion, ultimo_precio, iva = jdg.completar(
            codigo, descripcion, ultimo_precio, None
        )
        filas.append(
            {
                "codigo": codigo,
                "descripcion": descripcion,
                "ultimo_precio_compra_sistema": ultimo_precio,
                "unidades_sugeridas_tienda": unidades,
                "precio_proveedor": precio_prov,
                "iva_aplica": iva if iva is not None else True,
                "total": total,
                "observacion_tienda": _txt(r.get("observacion_tienda")),
            }
        )
    repo.reemplazar_items(pedido_id, filas)
    return len(filas)


def _limpiar_editor(pedido_id: int) -> None:
    st.session_state.pop(f"df_{pedido_id}", None)
    st.session_state.pop(f"ver_{pedido_id}", None)


def _buscar_producto(pid: int, actual: pd.DataFrame) -> None:
    """Busca por código o descripción y agrega una fila, conservando lo escrito.

    El buscador (lista de todo el catálogo) solo se carga al activar la casilla,
    para no ralentizar el tecleo normal de códigos.
    """
    if not jdg.disponible():
        return
    if not st.checkbox(
        "🔎 Buscar y agregar producto por descripción", key=f"chk_buscar_{pid}"
    ):
        return
    st.caption("El código se puede escribir directamente en la tabla.")
    c1, c2 = st.columns([6, 1])
    with c1:
        sel = st.selectbox(
            "Producto", options=["(elige)"] + jdg.descripciones(),
            key=f"buscar_{pid}", label_visibility="collapsed",
        )
    with c2:
        agregar = st.button("➕ Agregar", key=f"add_{pid}")
    if agregar:
        cod = jdg.codigo_de_descripcion(sel)
        if cod:
            fila = {c: None for c in COLUMNAS_ITEMS}
            fila["codigo"] = cod
            st.session_state[f"df_{pid}"] = pd.concat(
                [actual, pd.DataFrame([fila])], ignore_index=True
            )
            st.session_state[f"ver_{pid}"] = st.session_state.get(f"ver_{pid}", 0) + 1
            st.rerun()


# ----------------------------------------------------------------------
# Secciones
# ----------------------------------------------------------------------
def _nuevo_proveedor_expander() -> None:
    with st.expander("➕ Registrar un proveedor nuevo"):
        with st.form("nuevo_proveedor"):
            nombre = st.text_input("Nombre del proveedor")
            ruc = st.text_input("RUC (opcional)")
            dias = st.number_input(
                "Días de crédito habitual (opcional)", min_value=0, step=1, value=0
            )
            if st.form_submit_button("Guardar proveedor"):
                if not nombre.strip():
                    st.warning("Ponle un nombre al proveedor.")
                else:
                    repo.crear_proveedor(nombre.strip(), ruc.strip() or None, int(dias) or None)
                    st.success(f"Proveedor '{nombre}' guardado.")
                    st.rerun()


def _paso_crear(usuario: dict) -> None:
    st.subheader("1) Datos de la cita")
    nombres_jdg = jdg.proveedores()
    nombres_local = [p["nombre"] for p in repo.listar_proveedores()]
    nombres = sorted({*nombres_jdg, *nombres_local})

    if not nombres:
        st.warning("No hay proveedores. Registra uno abajo.")
    else:
        nombre = st.selectbox("Proveedor (escribe para buscar)", options=nombres)
        fecha = st.date_input("Fecha de la cita", value=date.today())
        if st.button("Crear pedido y empezar el sugerido", type="primary"):
            prov = repo.obtener_o_crear_proveedor(nombre)
            pedido = repo.crear_pedido(prov["id"], fecha, responsable=usuario["email"])
            _limpiar_editor(pedido["id"])
            st.session_state["pedido_tienda"] = pedido
            st.rerun()

    st.caption(
        f"Se listan {len(nombres_jdg)} proveedores de JDG. Si falta alguno, "
        "regístralo abajo."
    )
    _nuevo_proveedor_expander()


def _paso_sugerido(pedido: dict) -> None:
    provs = _mapa_proveedores()
    pid = pedido["id"]
    st.subheader(f"Pedido {pedido['numero_pedido']}")
    st.caption(
        f"Proveedor: **{provs.get(pedido['proveedor_id'], '—')}**  ·  "
        f"Estado: {modelo.etiqueta(pedido['estado'])}"
    )

    st.subheader("2) Sugerido")
    st.caption(
        "Escribe el **código** y sal de la celda: descripción, fecha y costo de la "
        "última compra se completan solos desde JDG. O usa el buscador por nombre."
    )

    version = st.session_state.get(f"ver_{pid}", 0)
    df_base = st.session_state.get(f"df_{pid}")
    if df_base is None:
        df_base = _df_items(pid)

    editado = st.data_editor(
        df_base,
        column_config=CONFIG_COLUMNAS,
        column_order=COLUMNAS_ITEMS,
        disabled=COLS_LECTURA,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key=f"editor_{pid}_{version}",
    )

    # Autocompletado en vivo.
    enriquecido, cambio = _enriquecer(editado)
    if cambio:
        st.session_state[f"df_{pid}"] = enriquecido
        st.session_state[f"ver_{pid}"] = version + 1
        st.rerun()

    _buscar_producto(pid, editado)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 Enviar a análisis", type="primary"):
            n = _guardar_items(pid, editado)
            if n == 0:
                st.warning("Agrega al menos una línea antes de enviar.")
            else:
                repo.cambiar_estado(pid, "en_analisis")
                _limpiar_editor(pid)
                st.session_state.pop("pedido_tienda", None)
                st.success(f"Pedido {pedido['numero_pedido']} enviado al administrador.")
                st.rerun()
    with col2:
        if st.button("💾 Guardar y salir (continuar después)"):
            _guardar_items(pid, editado)
            _limpiar_editor(pid)
            st.session_state.pop("pedido_tienda", None)
            st.rerun()


# ----------------------------------------------------------------------
# Entrada
# ----------------------------------------------------------------------
def render(usuario: dict) -> None:
    ui.encabezado("Responsable de tienda")
    if "pedido_tienda" in st.session_state:
        _paso_sugerido(st.session_state["pedido_tienda"])
        return

    seccion = st.sidebar.radio("Menú", ["Nuevo pedido", "Buscar pedidos"])
    if seccion == "Nuevo pedido":
        _paso_crear(usuario)
    else:
        vista_tablero.render(usuario)
