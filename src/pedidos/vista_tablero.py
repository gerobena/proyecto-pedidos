"""Tablero de pedidos: búsqueda por número/estado/proveedor y detalle."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from . import modelo
from . import repositorio as repo

# Columnas del detalle de líneas (solo lectura).
_COLS_DETALLE = {
    "codigo": "Código",
    "descripcion": "Descripción",
    "unidades_sugeridas_tienda": "Sug. tienda",
    "unidades_ajustadas_admin": "Unid. finales",
    "precio_proveedor": "Precio sugerido",
    "precio_final_acordado": "Precio final",
    "total": "Total",
    "comentario_admin": "Observación",
}


def _mostrar_detalle(pedido_id: int, provs: dict) -> None:
    pedido = repo.obtener_pedido(pedido_id)
    if pedido is None:
        st.error("El pedido ya no existe.")
        return

    st.markdown(f"### Pedido {pedido['numero_pedido']}")
    st.caption(
        f"Proveedor: **{provs.get(pedido['proveedor_id'], '—')}**  ·  "
        f"Estado: {modelo.etiqueta(pedido['estado'])}  ·  "
        f"Responsable: {pedido.get('responsable') or '—'}  ·  "
        f"Cita: {pedido.get('fecha_cita') or '—'}"
    )
    cond = []
    if pedido.get("dias_credito"):
        cond.append(f"{pedido['dias_credito']} días de crédito")
    if pedido.get("descuento_pct"):
        cond.append(f"{pedido['descuento_pct']:.1f}% de descuento")
    if cond:
        st.caption("Condiciones: " + " · ".join(cond))
    if pedido.get("comentario_admin"):
        st.markdown(f"**📝 Observación del administrador:** {pedido['comentario_admin']}")

    items = repo.listar_items(pedido_id)
    if not items:
        st.info("Este pedido no tiene líneas.")
        return
    df = pd.DataFrame(items)
    for c in _COLS_DETALLE:
        if c not in df.columns:
            df[c] = None
    vista = df[list(_COLS_DETALLE.keys())].rename(columns=_COLS_DETALLE)
    st.dataframe(vista, width="stretch", hide_index=True)


def render(usuario: dict) -> None:
    st.subheader("Tablero de pedidos")
    pedidos = repo.listar_pedidos()
    if not pedidos:
        st.info("Todavía no hay pedidos.")
        return
    provs = {p["id"]: p["nombre"] for p in repo.listar_proveedores()}

    c1, c2, c3 = st.columns(3)
    with c1:
        texto = st.text_input("Buscar por número", placeholder="PED-2026-…")
    with c2:
        estados = ["(todos)"] + modelo.ESTADOS
        est = st.selectbox(
            "Estado",
            estados,
            format_func=lambda e: e if e == "(todos)" else modelo.etiqueta(e),
        )
    with c3:
        nombres = ["(todos)"] + sorted({v for v in provs.values()})
        prov = st.selectbox("Proveedor", nombres)

    filtrados = []
    for p in pedidos:
        if texto and texto.strip().lower() not in (p["numero_pedido"] or "").lower():
            continue
        if est != "(todos)" and p["estado"] != est:
            continue
        if prov != "(todos)" and provs.get(p["proveedor_id"]) != prov:
            continue
        filtrados.append(p)

    if not filtrados:
        st.info("No hay pedidos que coincidan con el filtro.")
        return

    tabla = pd.DataFrame(
        [
            {
                "Número": p["numero_pedido"],
                "Proveedor": provs.get(p["proveedor_id"], "—"),
                "Estado": modelo.etiqueta(p["estado"]),
                "Fecha cita": p.get("fecha_cita") or "—",
                "Crédito": f"{p['dias_credito']} d" if p.get("dias_credito") else "—",
                "Desc. %": (
                    f"{p['descuento_pct']:.1f}%" if p.get("descuento_pct") else "—"
                ),
            }
            for p in filtrados
        ]
    )
    st.dataframe(tabla, width="stretch", hide_index=True)

    por_numero = {p["numero_pedido"]: p for p in filtrados}
    numero = st.selectbox("Ver / abrir pedido", options=list(por_numero.keys()))
    sel = por_numero[numero]
    rol = usuario.get("rol")
    es_sugerido = sel["estado"] == "sugerido"
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("👁️ Ver detalle"):
            st.session_state["tablero_detalle_id"] = sel["id"]
            st.rerun()
    with col2:
        if rol == "administrador":
            if st.button("✏️ Abrir para trabajar", type="primary"):
                st.session_state["pedido_admin_id"] = sel["id"]
                st.rerun()
        elif rol == "tienda" and es_sugerido:
            if st.button("✏️ Editar sugerido", type="primary"):
                st.session_state["pedido_tienda"] = sel
                st.rerun()
    with col3:
        # Eliminar solo pedidos en Sugerido, con confirmación.
        if es_sugerido:
            conf = st.checkbox("Confirmar", key=f"delc_{sel['id']}")
            if st.button("🗑️ Eliminar", disabled=not conf):
                repo.eliminar_pedido(sel["id"])
                st.session_state.pop("tablero_detalle_id", None)
                st.success(f"Pedido {sel['numero_pedido']} eliminado.")
                st.rerun()

    if rol == "tienda" and not es_sugerido:
        st.caption(
            "Solo puedes editar/eliminar pedidos en estado 📝 Sugerido. Si está en "
            "análisis, pídele al administrador que lo devuelva a tienda."
        )

    # Detalle a ancho completo (fuera de las columnas).
    det_id = st.session_state.get("tablero_detalle_id")
    if det_id is not None:
        st.divider()
        if st.button("Ocultar detalle"):
            st.session_state.pop("tablero_detalle_id", None)
            st.rerun()
        _mostrar_detalle(det_id, provs)
