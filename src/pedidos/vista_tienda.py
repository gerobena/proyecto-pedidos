"""Vista del Responsable de tienda: crear el pedido y registrar el sugerido."""
from __future__ import annotations

import math
from datetime import date

import pandas as pd
import streamlit as st

from . import modelo
from . import repositorio as repo

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
        total = round(unidades * precio_prov, 2) if unidades and precio_prov else None
        filas.append(
            {
                "codigo": codigo,
                "descripcion": descripcion,
                "unidades_sugeridas_tienda": unidades,
                "ultimo_precio_compra_sistema": _num(
                    r.get("ultimo_precio_compra_sistema")
                ),
                "precio_proveedor": precio_prov,
                "iva_aplica": bool(iva) if iva is not None else True,
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
    proveedores = repo.listar_proveedores()
    if not proveedores:
        st.warning("No hay proveedores todavía. Registra uno abajo.")
    else:
        opciones = {p["id"]: p["nombre"] for p in proveedores}
        prov_id = st.selectbox(
            "Proveedor",
            options=list(opciones.keys()),
            format_func=lambda i: opciones[i],
        )
        fecha = st.date_input("Fecha de la cita", value=date.today())
        if st.button("Crear pedido y empezar el sugerido", type="primary"):
            pedido = repo.crear_pedido(prov_id, fecha, responsable=usuario["email"])
            st.session_state["pedido_tienda"] = pedido
            st.rerun()

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
    df = _df_items(pedido["id"])
    editado = st.data_editor(
        df,
        column_config=CONFIG_COLUMNAS,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"editor_{pedido['id']}",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 Guardar líneas"):
            n = _guardar_items(pedido["id"], editado)
            st.success(f"Guardadas {n} líneas.")
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


def _mis_pedidos() -> None:
    st.subheader("Mis pedidos")
    pedidos = repo.listar_pedidos()
    if not pedidos:
        st.info("Todavía no hay pedidos.")
        return
    provs = _mapa_proveedores()
    tabla = pd.DataFrame(
        [
            {
                "Número": p["numero_pedido"],
                "Proveedor": provs.get(p["proveedor_id"], "—"),
                "Estado": modelo.etiqueta(p["estado"]),
                "Fecha cita": p.get("fecha_cita") or "—",
            }
            for p in pedidos
        ]
    )
    st.dataframe(tabla, use_container_width=True, hide_index=True)


# ----------------------------------------------------------------------
# Entrada
# ----------------------------------------------------------------------
def render(usuario: dict) -> None:
    st.title("📦 Pedidos JDG — Tienda")
    seccion = st.sidebar.radio("Menú", ["Nuevo pedido", "Mis pedidos"])

    if seccion == "Nuevo pedido":
        if "pedido_tienda" in st.session_state:
            _paso_sugerido(st.session_state["pedido_tienda"])
        else:
            _paso_crear(usuario)
    else:
        _mis_pedidos()
