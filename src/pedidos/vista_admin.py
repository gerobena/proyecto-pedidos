"""Vista del Administrador: analizar el sugerido, ajustar, negociar y enviar.

El administrador puede:
- ajustar las unidades de cada línea de tienda,
- cerrar un **precio final acordado** (distinto de la oferta inicial),
- **agregar productos nuevos** que surjan en la negociación,
- fijar condiciones del pedido (crédito, descuento) y comentar.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from . import modelo
from . import repositorio as repo
from .util import num, txt

# Columnas de referencia (vienen de tienda / sistema): NO editables.
COLS_REFERENCIA = [
    "unidades_sugeridas_tienda",
    "precio_proveedor",
    "ultimo_precio_compra_sistema",
    "observacion_tienda",
]

# Orden de columnas: primero las de referencia (tienda/sistema), y al final las
# tres que edita el administrador (unidades finales, precio final, IVA).
ORDEN_COLUMNAS = [
    "codigo",
    "descripcion",
    "unidades_sugeridas_tienda",
    "precio_proveedor",
    "ultimo_precio_compra_sistema",
    "observacion_tienda",
    "unidades_ajustadas_admin",
    "precio_final_acordado",
    "iva_aplica",
]

CONFIG_COLUMNAS = {
    "codigo": st.column_config.TextColumn("Código"),
    "descripcion": st.column_config.TextColumn("Descripción", width="medium"),
    "unidades_sugeridas_tienda": st.column_config.NumberColumn("Sug. tienda"),
    "unidades_ajustadas_admin": st.column_config.NumberColumn(
        "✏️ Unid. finales", min_value=0, step=1
    ),
    "precio_proveedor": st.column_config.NumberColumn("Oferta prov.", format="%.2f"),
    "precio_final_acordado": st.column_config.NumberColumn(
        "✏️ Precio final", help="Precio de compra acordado tras negociar", format="%.2f"
    ),
    "ultimo_precio_compra_sistema": st.column_config.NumberColumn(
        "Últ. sistema", format="%.2f"
    ),
    "iva_aplica": st.column_config.CheckboxColumn("✏️ ¿IVA?", default=True),
    "observacion_tienda": st.column_config.TextColumn("Obs. tienda", width="medium"),
}


# ----------------------------------------------------------------------
# Tabla de ítems
# ----------------------------------------------------------------------
def _df_items(items: list[dict]) -> pd.DataFrame:
    """DataFrame para el editor del admin. Sin columna id (se reescribe todo)."""
    if items:
        df = pd.DataFrame(items)
        for c in ORDEN_COLUMNAS:
            if c not in df.columns:
                df[c] = None
        df = df[ORDEN_COLUMNAS]
        # Arranca desde lo de tienda: unidades finales = sugeridas si no hay ajuste;
        # precio final = oferta del proveedor mientras no se negocie otro.
        df["unidades_ajustadas_admin"] = df["unidades_ajustadas_admin"].fillna(
            df["unidades_sugeridas_tienda"]
        )
        df["precio_final_acordado"] = df["precio_final_acordado"].fillna(
            df["precio_proveedor"]
        )
        return df

    fila_vacia = {c: (True if c == "iva_aplica" else None) for c in ORDEN_COLUMNAS}
    return pd.DataFrame([fila_vacia])


def _guardar_items(pedido_id: int, df: pd.DataFrame) -> int:
    """Reescribe las líneas del pedido con lo que el admin dejó (incluye filas nuevas)."""
    filas: list[dict] = []
    for _, r in df.iterrows():
        codigo = txt(r.get("codigo"))
        descripcion = txt(r.get("descripcion"))
        if not codigo and not descripcion:
            continue  # fila vacía

        u_sug = num(r.get("unidades_sugeridas_tienda"))
        u_fin = num(r.get("unidades_ajustadas_admin"))
        p_prov = num(r.get("precio_proveedor"))
        p_fin = num(r.get("precio_final_acordado"))
        iva = r.get("iva_aplica")

        unidades = u_fin if u_fin is not None else u_sug
        precio = p_fin if p_fin is not None else p_prov
        total = round(unidades * precio, 2) if unidades and precio else None

        filas.append(
            {
                "codigo": codigo,
                "descripcion": descripcion,
                "unidades_sugeridas_tienda": u_sug,
                "unidades_ajustadas_admin": u_fin,
                "ultimo_precio_compra_sistema": num(r.get("ultimo_precio_compra_sistema")),
                "precio_proveedor": p_prov,
                "precio_final_acordado": p_fin,
                "iva_aplica": bool(iva) if iva is not None else True,
                "total": total,
                "observacion_tienda": txt(r.get("observacion_tienda")),
            }
        )
    repo.reemplazar_items(pedido_id, filas)
    return len(filas)


def _total_pedido(df: pd.DataFrame) -> float:
    """Total en dólares: suma de (unidades finales × precio final) por línea.

    Usa el ajuste del admin si existe; si no, cae a lo de tienda. Los precios ya
    vienen con IVA cuando aplica, así que el total es el desembolso real.
    """
    total = 0.0
    for _, r in df.iterrows():
        if not txt(r.get("codigo")) and not txt(r.get("descripcion")):
            continue
        unidades = num(r.get("unidades_ajustadas_admin"))
        if unidades is None:
            unidades = num(r.get("unidades_sugeridas_tienda"))
        precio = num(r.get("precio_final_acordado"))
        if precio is None:
            precio = num(r.get("precio_proveedor"))
        if unidades and precio:
            total += unidades * precio
    return round(total, 2)


def _guardar_condiciones(
    pedido_id: int, dias: int, descuento: float, comentario: str
) -> None:
    repo.actualizar_cabecera(
        pedido_id,
        {
            "dias_credito": int(dias) if dias else None,
            "descuento_pct": float(descuento) if descuento else None,
            "comentario_admin": txt(comentario),
        },
    )


# ----------------------------------------------------------------------
# Bandeja
# ----------------------------------------------------------------------
def _bandeja() -> None:
    st.subheader("Bandeja de pedidos")
    estado_sel = st.selectbox(
        "Ver pedidos en estado",
        options=modelo.ESTADOS,
        index=modelo.ESTADOS.index("en_analisis"),
        format_func=modelo.etiqueta,
    )
    pedidos = repo.listar_pedidos([estado_sel])
    if not pedidos:
        st.info(f"No hay pedidos en estado «{modelo.etiqueta(estado_sel)}».")
        return

    provs = {p["id"]: p["nombre"] for p in repo.listar_proveedores()}
    tabla = pd.DataFrame(
        [
            {
                "Número": p["numero_pedido"],
                "Proveedor": provs.get(p["proveedor_id"], "—"),
                "Fecha cita": p.get("fecha_cita") or "—",
                "Responsable": p.get("responsable") or "—",
            }
            for p in pedidos
        ]
    )
    st.dataframe(tabla, use_container_width=True, hide_index=True)

    por_numero = {p["numero_pedido"]: p["id"] for p in pedidos}
    numero = st.selectbox("Abrir pedido", options=list(por_numero.keys()))
    if st.button("Abrir", type="primary"):
        st.session_state["pedido_admin_id"] = por_numero[numero]
        st.rerun()


# ----------------------------------------------------------------------
# Análisis de un pedido
# ----------------------------------------------------------------------
def _analizar(pedido_id: int) -> None:
    pedido = repo.obtener_pedido(pedido_id)
    if pedido is None:
        st.error("El pedido ya no existe.")
        st.session_state.pop("pedido_admin_id", None)
        return

    provs = {p["id"]: p["nombre"] for p in repo.listar_proveedores()}

    if st.button("⬅️ Volver a la bandeja"):
        st.session_state.pop("pedido_admin_id", None)
        st.rerun()

    st.subheader(f"Pedido {pedido['numero_pedido']}")
    st.caption(
        f"Proveedor: **{provs.get(pedido['proveedor_id'], '—')}**  ·  "
        f"Estado: {modelo.etiqueta(pedido['estado'])}  ·  "
        f"Responsable: {pedido.get('responsable') or '—'}"
    )

    # --- Ítems: ajustar, negociar precio y agregar productos ---
    st.markdown("#### Ítems del pedido")
    st.caption(
        "Las columnas con ✏️ son editables. Puedes **ajustar unidades**, cerrar el "
        "**precio final**, y **agregar productos nuevos** en las filas de abajo "
        "(escribe código y descripción). Lo de tienda queda de referencia."
    )
    df = _df_items(repo.listar_items(pedido_id))
    editado = st.data_editor(
        df,
        column_config=CONFIG_COLUMNAS,
        column_order=ORDEN_COLUMNAS,
        disabled=COLS_REFERENCIA,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"editor_admin_{pedido_id}",
    )

    # --- Total del pedido (se recalcula en vivo con lo editado) ---
    total = _total_pedido(editado)
    st.metric(
        "💵 Total del pedido (unidades finales × precio final)",
        f"${total:,.2f}",
    )

    # --- Condiciones del pedido (cabecera) ---
    st.markdown("#### Condiciones acordadas")
    c1, c2 = st.columns(2)
    with c1:
        dias = st.number_input(
            "Días de crédito", min_value=0, step=1, value=int(pedido.get("dias_credito") or 0)
        )
    with c2:
        descuento = st.number_input(
            "Descuento (%)",
            min_value=0.0,
            max_value=100.0,
            step=0.5,
            value=float(pedido.get("descuento_pct") or 0.0),
        )
    if descuento:
        con_desc = round(total * (1 - descuento / 100), 2)
        st.caption(
            f"Total con {descuento:.1f}% de descuento: **${con_desc:,.2f}**"
        )
    comentario = st.text_area(
        "Comentario del administrador",
        value=pedido.get("comentario_admin") or "",
        placeholder="Ej.: se acordó 60 días de crédito y 5% por volumen.",
    )

    # --- Acciones ---
    st.divider()
    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("💾 Guardar análisis"):
            n = _guardar_items(pedido_id, editado)
            _guardar_condiciones(pedido_id, dias, descuento, comentario)
            st.success(f"Análisis guardado ({n} líneas).")
    with a2:
        if st.button("📤 Marcar como enviado", type="primary"):
            _guardar_items(pedido_id, editado)
            _guardar_condiciones(pedido_id, dias, descuento, comentario)
            repo.cambiar_estado(pedido_id, "enviado")
            st.session_state.pop("pedido_admin_id", None)
            st.success(f"Pedido {pedido['numero_pedido']} marcado como enviado.")
            st.rerun()
    with a3:
        if st.button("↩️ Devolver a tienda"):
            _guardar_items(pedido_id, editado)
            _guardar_condiciones(pedido_id, dias, descuento, comentario)
            repo.cambiar_estado(pedido_id, "sugerido")
            st.session_state.pop("pedido_admin_id", None)
            st.info(f"Pedido {pedido['numero_pedido']} devuelto a tienda.")
            st.rerun()


# ----------------------------------------------------------------------
# Entrada
# ----------------------------------------------------------------------
def render(usuario: dict) -> None:
    st.title("📦 Pedidos JDG — Administrador")
    if "pedido_admin_id" in st.session_state:
        _analizar(st.session_state["pedido_admin_id"])
    else:
        _bandeja()
