"""Vista del Responsable de tienda: crear el pedido y registrar el sugerido."""
from __future__ import annotations

import math
from datetime import date

import pandas as pd
import streamlit as st

from . import jdg
from . import modelo
from . import repositorio as repo
from . import vista_jdg
from . import vista_tablero

# Columnas que la tienda llena en el sugerido.
COLUMNAS_ITEMS = [
    "codigo",
    "descripcion",
    "unidades_sugeridas_tienda",
    "ultimo_precio_compra_sistema",
    "precio_proveedor",
    "iva_aplica",
    "observacion_tienda",
]

CONFIG_COLUMNAS = {
    "codigo": st.column_config.TextColumn("Código"),
    "descripcion": st.column_config.TextColumn("Descripción", width="large"),
    "unidades_sugeridas_tienda": st.column_config.NumberColumn(
        "Unid. sugeridas", min_value=0, step=1
    ),
    "ultimo_precio_compra_sistema": st.column_config.NumberColumn(
        "Últ. precio sistema", help="Con IVA si aplica", format="%.2f"
    ),
    "precio_proveedor": st.column_config.NumberColumn(
        "Precio proveedor", help="Con IVA si aplica", format="%.2f"
    ),
    "iva_aplica": st.column_config.CheckboxColumn("¿IVA?", default=True),
    "observacion_tienda": st.column_config.TextColumn("Observación", width="large"),
}


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


def _df_items(pedido_id: int | None) -> pd.DataFrame:
    """DataFrame para el editor: ítems existentes o una plantilla vacía."""
    items = repo.listar_items(pedido_id) if pedido_id else []
    if items:
        df = pd.DataFrame(items)
        for c in COLUMNAS_ITEMS:
            if c not in df.columns:
                df[c] = None
        return df[COLUMNAS_ITEMS]
    fila_vacia = {c: (True if c == "iva_aplica" else None) for c in COLUMNAS_ITEMS}
    return pd.DataFrame([fila_vacia])


def _guardar_items(pedido_id: int, df: pd.DataFrame) -> int:
    filas: list[dict] = []
    for _, r in df.iterrows():
        codigo = _txt(r.get("codigo"))
        descripcion = _txt(r.get("descripcion"))
        if not codigo and not descripcion:
            continue  # fila vacía, se ignora
        unidades = _num(r.get("unidades_sugeridas_tienda"))
        precio_prov = _num(r.get("precio_proveedor"))
        iva = r.get("iva_aplica")
        iva = bool(iva) if iva is not None else True
        total = round(unidades * precio_prov, 2) if unidades and precio_prov else None

        # Autocompletar desde JDG: descripción, último precio (con IVA si aplica) e IVA.
        ultimo_precio = _num(r.get("ultimo_precio_compra_sistema"))
        descripcion, ultimo_precio, iva = jdg.completar(
            codigo, descripcion, ultimo_precio, iva
        )

        filas.append(
            {
                "codigo": codigo,
                "descripcion": descripcion,
                "unidades_sugeridas_tienda": unidades,
                "ultimo_precio_compra_sistema": ultimo_precio,
                "precio_proveedor": precio_prov,
                "iva_aplica": iva,
                "total": total,
                "observacion_tienda": _txt(r.get("observacion_tienda")),
            }
        )
    repo.reemplazar_items(pedido_id, filas)
    return len(filas)


def _mapa_proveedores() -> dict[int, str]:
    return {p["id"]: p["nombre"] for p in repo.listar_proveedores()}


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
                    repo.crear_proveedor(
                        nombre.strip(),
                        ruc.strip() or None,
                        int(dias) or None,
                    )
                    st.success(f"Proveedor '{nombre}' guardado.")
                    st.rerun()


def _paso_crear(usuario: dict) -> None:
    st.subheader("1) Datos de la cita")
    # Lista de proveedores: los que ya conoce JDG + los guardados en local.
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
            st.session_state["pedido_tienda"] = pedido
            st.rerun()

    st.caption(
        f"Se listan {len(nombres_jdg)} proveedores de JDG. Si falta alguno "
        "(proveedor nuevo), regístralo abajo."
    )
    _nuevo_proveedor_expander()


def _paso_sugerido(pedido: dict) -> None:
    provs = _mapa_proveedores()
    st.subheader(f"Pedido {pedido['numero_pedido']}")
    st.caption(
        f"Proveedor: **{provs.get(pedido['proveedor_id'], '—')}**  ·  "
        f"Estado: {modelo.etiqueta(pedido['estado'])}"
    )

    st.subheader("2) Sugerido")
    st.caption(
        "Agrega una fila por producto. El **Total** se calcula solo "
        "(unidades × precio proveedor) al guardar."
    )
    version = st.session_state.get(f"ver_{pedido['id']}", 0)
    df = _df_items(pedido["id"])
    editado = st.data_editor(
        df,
        column_config=CONFIG_COLUMNAS,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key=f"editor_{pedido['id']}_{version}",
    )

    with st.expander("🔎 Datos de JDG (apoyo)"):
        st.caption(
            "Al guardar, la descripción y el último precio se autocompletan "
            "desde JDG para los códigos que existan."
        )
        vista_jdg.panel(editado["codigo"].tolist())

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 Guardar líneas"):
            n = _guardar_items(pedido["id"], editado)
            st.session_state[f"ver_{pedido['id']}"] = version + 1
            st.success(f"Guardadas {n} líneas.")
            st.rerun()
    with col2:
        if st.button("📤 Enviar a análisis", type="primary"):
            n = _guardar_items(pedido["id"], editado)
            if n == 0:
                st.warning("Agrega al menos una línea antes de enviar.")
            else:
                repo.cambiar_estado(pedido["id"], "en_analisis")
                st.session_state.pop("pedido_tienda", None)
                st.success(
                    f"Pedido {pedido['numero_pedido']} enviado al administrador."
                )
                st.rerun()
    with col3:
        if st.button("Salir sin enviar"):
            _guardar_items(pedido["id"], editado)
            st.session_state.pop("pedido_tienda", None)
            st.rerun()


# ----------------------------------------------------------------------
# Entrada
# ----------------------------------------------------------------------
def render(usuario: dict) -> None:
    st.title("📦 Pedidos JDG — Tienda")
    # Un pedido abierto (nuevo o reabierto para editar) tiene prioridad.
    if "pedido_tienda" in st.session_state:
        _paso_sugerido(st.session_state["pedido_tienda"])
        return

    seccion = st.sidebar.radio("Menú", ["Nuevo pedido", "Buscar pedidos"])
    if seccion == "Nuevo pedido":
        _paso_crear(usuario)
    else:
        vista_tablero.render(usuario)
