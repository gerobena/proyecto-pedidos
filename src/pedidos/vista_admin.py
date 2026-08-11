"""Vista del Administrador: analizar el sugerido, negociar, cerrar y generar PDF."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from . import jdg
from . import modelo
from . import pdf as pdf_mod
from . import repositorio as repo
from . import ui
from . import vista_tablero
from .util import iguales, num, txt

COLS_REFERENCIA = [
    "fecha_ult_compra",
    "unidades_sugeridas_tienda",
    "precio_proveedor",
    "ultimo_precio_compra_sistema",
    "observacion_tienda",
    "unidad_prom_mes",
    "dias_prom_venta",
]

ORDEN_COLUMNAS = [
    "codigo",
    "descripcion",
    "fecha_ult_compra",
    "unidades_sugeridas_tienda",
    "precio_proveedor",
    "ultimo_precio_compra_sistema",
    "observacion_tienda",
    "unidad_prom_mes",
    "dias_prom_venta",
    "unidades_ajustadas_admin",
    "precio_final_acordado",
    "comentario_admin",
]

CONFIG_COLUMNAS = {
    "codigo": st.column_config.TextColumn("Código"),
    "descripcion": st.column_config.TextColumn("Descripción", width="medium"),
    "fecha_ult_compra": st.column_config.TextColumn("Fecha últ. compra"),
    "unidades_sugeridas_tienda": st.column_config.NumberColumn("Unid. sugerido"),
    "precio_proveedor": st.column_config.NumberColumn("Precio sugerido", format="%.2f"),
    "ultimo_precio_compra_sistema": st.column_config.NumberColumn(
        "Últ. precio sistema", format="%.2f"
    ),
    "observacion_tienda": st.column_config.TextColumn("Obs. almacén", width="medium"),
    "unidad_prom_mes": st.column_config.NumberColumn(
        "Unid. prom/mes", help="Unidades vendidas por mes en promedio", format="%.2f"
    ),
    "dias_prom_venta": st.column_config.NumberColumn(
        "Días prom. venta",
        help="Días promedio (FIFO) que tarda en venderse una unidad",
        format="%.0f",
    ),
    "unidades_ajustadas_admin": st.column_config.NumberColumn(
        "✏️ Unid. finales", min_value=0, step=1
    ),
    "precio_final_acordado": st.column_config.NumberColumn(
        "✏️ Precio final", help="Por defecto el último precio del sistema",
        format="%.2f",
    ),
    "comentario_admin": st.column_config.TextColumn("✏️ Observación", width="medium"),
}


# ----------------------------------------------------------------------
# Tabla de ítems
# ----------------------------------------------------------------------
def _enriquecer(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    """Trae de JDG los datos del código de cada fila y aplica los valores por defecto.

    Sobreescribe los campos de referencia si el código cambió (así al cambiar el
    código se actualizan los datos). Cuando el costo cambia, el precio final por
    defecto sigue al nuevo costo.
    """
    df = df.copy()
    cambio = False
    for idx, r in df.iterrows():
        cod = txt(r.get("codigo"))
        info = jdg.info(cod) if cod else None
        if info:
            desc_j = info.get("descripcion")
            if desc_j and txt(r.get("descripcion")) != desc_j:
                df.at[idx, "descripcion"] = desc_j
                cambio = True
            costo_j = info.get("ultimo_precio_con_iva")
            if costo_j is not None and not iguales(
                num(r.get("ultimo_precio_compra_sistema")), costo_j
            ):
                df.at[idx, "ultimo_precio_compra_sistema"] = costo_j
                df.at[idx, "precio_final_acordado"] = costo_j  # default sigue al costo
                cambio = True
            fecha = info.get("fecha_ult_compra")
            fecha_j = str(fecha)[:10] if fecha is not None else None
            if fecha_j and txt(r.get("fecha_ult_compra")) != fecha_j:
                df.at[idx, "fecha_ult_compra"] = fecha_j
                cambio = True
            prom_j = info.get("unidad_prom_mes")
            if prom_j is not None and not iguales(num(r.get("unidad_prom_mes")), prom_j):
                df.at[idx, "unidad_prom_mes"] = prom_j
                cambio = True
            dias_j = info.get("dias_prom_venta")
            if dias_j is not None and not iguales(num(r.get("dias_prom_venta")), dias_j):
                df.at[idx, "dias_prom_venta"] = dias_j
                cambio = True
        # Valores por defecto de las columnas editables (filas nuevas / sin ajuste).
        if num(r.get("unidades_ajustadas_admin")) is None and num(
            r.get("unidades_sugeridas_tienda")
        ) is not None:
            df.at[idx, "unidades_ajustadas_admin"] = num(r.get("unidades_sugeridas_tienda"))
            cambio = True
        if num(df.at[idx, "precio_final_acordado"]) is None:
            up = num(df.at[idx, "ultimo_precio_compra_sistema"])
            if up is not None:
                df.at[idx, "precio_final_acordado"] = up  # por defecto, últ. precio sistema
                cambio = True
    return df, cambio


def _df_items(items: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(items) if items else pd.DataFrame([{}])
    for c in ORDEN_COLUMNAS:
        if c not in df.columns:
            df[c] = None
    df, _ = _enriquecer(df[ORDEN_COLUMNAS])
    return df


def _guardar_items(pedido_id: int, df: pd.DataFrame) -> int:
    filas: list[dict] = []
    for _, r in df.iterrows():
        codigo = txt(r.get("codigo"))
        descripcion = txt(r.get("descripcion"))
        if not codigo and not descripcion:
            continue
        u_sug = num(r.get("unidades_sugeridas_tienda"))
        u_fin = num(r.get("unidades_ajustadas_admin"))
        p_prov = num(r.get("precio_proveedor"))
        p_fin = num(r.get("precio_final_acordado"))
        unidades = u_fin if u_fin is not None else u_sug
        precio = p_fin if p_fin is not None else p_prov
        total = round(unidades * precio, 2) if unidades and precio else None
        ultimo_precio = num(r.get("ultimo_precio_compra_sistema"))
        descripcion, ultimo_precio, iva = jdg.completar(
            codigo, descripcion, ultimo_precio, None
        )
        filas.append(
            {
                "codigo": codigo,
                "descripcion": descripcion,
                "unidades_sugeridas_tienda": u_sug,
                "unidades_ajustadas_admin": u_fin,
                "ultimo_precio_compra_sistema": ultimo_precio,
                "precio_proveedor": p_prov,
                "precio_final_acordado": p_fin,
                "iva_aplica": iva if iva is not None else True,
                "total": total,
                "observacion_tienda": txt(r.get("observacion_tienda")),
                "comentario_admin": txt(r.get("comentario_admin")),
            }
        )
    repo.reemplazar_items(pedido_id, filas)
    return len(filas)


def _total_pedido(df: pd.DataFrame) -> float:
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


def _validar(df: pd.DataFrame) -> list[str]:
    """Alertas informativas. Un 0 es válido (el admin decidió no pedir ese ítem);
    solo se avisa cuando el campo se deja VACÍO."""
    errores, vistos = [], []
    for _, r in df.iterrows():
        cod = txt(r.get("codigo"))
        desc = txt(r.get("descripcion"))
        if not cod and not desc:
            continue
        etq = cod or desc
        if num(r.get("unidades_ajustadas_admin")) is None:
            errores.append(f"{etq}: falta unid. finales")
        if num(r.get("precio_final_acordado")) is None:
            errores.append(f"{etq}: falta precio final")
        if cod:
            if cod in vistos:
                errores.append(f"{cod}: código repetido")
            vistos.append(cod)
    return errores


def _guardar_condiciones(pedido_id: int, dias: int, descuento: float, comentario: str) -> None:
    repo.actualizar_cabecera(
        pedido_id,
        {
            "dias_credito": int(dias) if dias else None,
            "descuento_pct": float(descuento) if descuento else None,
            "comentario_admin": txt(comentario),
        },
    )


def _reset_editor(pid: int) -> None:
    st.session_state.pop(f"df_admin_{pid}", None)
    for k in (f"dias_{pid}", f"desc_{pid}", f"coment_{pid}"):
        st.session_state.pop(k, None)
    st.session_state[f"ver_admin_{pid}"] = st.session_state.get(f"ver_admin_{pid}", 0) + 1


def _buscar_producto(pid: int, actual: pd.DataFrame) -> None:
    """Busca por código o descripción y agrega una fila, conservando lo escrito.

    El buscador (catálogo completo) solo se carga al activar la casilla, para no
    ralentizar el tecleo normal de códigos.
    """
    if not jdg.disponible():
        return
    if not st.checkbox(
        "🔎 Buscar y agregar producto por descripción", key=f"chk_buscar_a_{pid}"
    ):
        return
    st.caption("El código se puede escribir directamente en la tabla.")
    c1, c2 = st.columns([6, 1])
    with c1:
        sel = st.selectbox(
            "Producto", options=["(elige)"] + jdg.descripciones(),
            key=f"buscar_a_{pid}", label_visibility="collapsed",
        )
    with c2:
        agregar = st.button("➕ Agregar", key=f"add_a_{pid}")
    if agregar:
        cod = jdg.codigo_de_descripcion(sel)
        if cod:
            fila = {c: None for c in ORDEN_COLUMNAS}
            fila["codigo"] = cod
            st.session_state[f"df_admin_{pid}"] = pd.concat(
                [actual, pd.DataFrame([fila])], ignore_index=True
            )
            st.session_state[f"ver_admin_{pid}"] = (
                st.session_state.get(f"ver_admin_{pid}", 0) + 1
            )
            st.rerun()


def _boton_pdf(pedido: dict, provs: dict) -> None:
    items = repo.listar_items(pedido["id"])
    if not items:
        return
    datos = pdf_mod.pedido_pdf(pedido, items, provs.get(pedido["proveedor_id"], "—"))
    st.download_button(
        "📄 Descargar PDF del pedido",
        data=datos,
        file_name=f"{pedido['numero_pedido']}.pdf",
        mime="application/pdf",
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
    st.dataframe(tabla, width="stretch", hide_index=True)

    por_numero = {p["numero_pedido"]: p["id"] for p in pedidos}
    numero = st.selectbox("Abrir pedido", options=list(por_numero.keys()))
    if st.button("Abrir", type="primary"):
        st.session_state["pedido_admin_id"] = por_numero[numero]
        st.rerun()


# ----------------------------------------------------------------------
# Detalle
# ----------------------------------------------------------------------
def _detalle(pedido_id: int) -> None:
    pedido = repo.obtener_pedido(pedido_id)
    if pedido is None:
        st.error("El pedido ya no existe.")
        st.session_state.pop("pedido_admin_id", None)
        return

    provs = {p["id"]: p["nombre"] for p in repo.listar_proveedores()}

    if st.button("⬅️ Volver"):
        st.session_state.pop("pedido_admin_id", None)
        st.rerun()

    st.subheader(f"Pedido {pedido['numero_pedido']}")
    st.caption(
        f"Proveedor: **{provs.get(pedido['proveedor_id'], '—')}**  ·  "
        f"Estado: {modelo.etiqueta(pedido['estado'])}  ·  "
        f"Responsable: {pedido.get('responsable') or '—'}"
    )

    if pedido["estado"] in ("sugerido", "en_analisis"):
        _negociacion(pedido, provs)
    else:
        _readonly(pedido, provs)


def _negociacion(pedido: dict, provs: dict) -> None:
    pid = pedido["id"]
    st.markdown("#### Ítems del pedido")
    st.caption(
        "Escribe el **código** (o usa el buscador por nombre) y se completan "
        "descripción, precio y métricas de JDG. Columnas con ✏️ editables. Puedes "
        "**agregar productos** que no vinieron de tienda."
    )

    version = st.session_state.get(f"ver_admin_{pid}", 0)
    df_base = st.session_state.get(f"df_admin_{pid}")
    if df_base is None:
        df_base = _df_items(repo.listar_items(pid))

    editado = st.data_editor(
        df_base,
        column_config=CONFIG_COLUMNAS,
        column_order=ORDEN_COLUMNAS,
        disabled=COLS_REFERENCIA,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key=f"editor_admin_{pid}_{version}",
    )

    enr, cambio = _enriquecer(editado)
    if cambio:
        st.session_state[f"df_admin_{pid}"] = enr
        st.session_state[f"ver_admin_{pid}"] = version + 1
        st.rerun()

    _buscar_producto(pid, editado)

    total = _total_pedido(editado)
    st.metric("💵 Total del pedido (unidades finales × precio final)", f"${total:,.2f}")

    st.markdown("#### Condiciones acordadas")
    # Widgets con key: su valor se conserva aunque el autocompletado haga rerun.
    kd, kdesc, kc = f"dias_{pid}", f"desc_{pid}", f"coment_{pid}"
    if kd not in st.session_state:
        st.session_state[kd] = int(pedido.get("dias_credito") or 0)
    if kdesc not in st.session_state:
        st.session_state[kdesc] = float(pedido.get("descuento_pct") or 0.0)
    if kc not in st.session_state:
        st.session_state[kc] = pedido.get("comentario_admin") or ""

    c1, c2 = st.columns(2)
    with c1:
        dias = st.number_input("Días de crédito", min_value=0, step=1, key=kd)
    with c2:
        descuento = st.number_input(
            "Descuento (%)", min_value=0.0, max_value=100.0, step=0.5, key=kdesc
        )
    if descuento:
        st.caption(
            f"Total con {descuento:.1f}% de descuento: "
            f"**${round(total * (1 - descuento / 100), 2):,.2f}**"
        )
    comentario = st.text_area(
        "Comentario del administrador (negociación)",
        key=kc,
        placeholder="Ej.: se acordó 60 días de crédito y 5% por volumen.",
    )

    st.divider()
    errores = _validar(editado)
    if errores:
        st.warning("Revisa antes de cerrar: " + "; ".join(errores[:6]))
    confirmar = st.checkbox("Confirmo cerrar el pedido (no se podrá editar).")

    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("💾 Guardar análisis"):
            _guardar_items(pid, editado)
            _guardar_condiciones(pid, dias, descuento, comentario)
            _reset_editor(pid)
            st.success("Análisis guardado.")
            st.rerun()
    with a2:
        if st.button("✅ Cerrar pedido", type="primary", disabled=not confirmar):
            _guardar_items(pid, editado)
            _guardar_condiciones(pid, dias, descuento, comentario)
            repo.cambiar_estado(pid, "cerrado")
            _reset_editor(pid)
            st.success(f"Pedido {pedido['numero_pedido']} cerrado.")
            st.rerun()
    with a3:
        if st.button("↩️ Devolver a tienda"):
            _guardar_items(pid, editado)
            _guardar_condiciones(pid, dias, descuento, comentario)
            repo.cambiar_estado(pid, "sugerido")
            _reset_editor(pid)
            st.session_state.pop("pedido_admin_id", None)
            st.info(f"Pedido {pedido['numero_pedido']} devuelto a tienda.")
            st.rerun()


def _readonly(pedido: dict, provs: dict) -> None:
    st.success("Pedido cerrado. Descarga el PDF con lo acordado.")
    cond = []
    if pedido.get("dias_credito"):
        cond.append(f"{pedido['dias_credito']} días de crédito")
    if pedido.get("descuento_pct"):
        cond.append(f"{pedido['descuento_pct']:.1f}% de descuento")
    if cond:
        st.caption("Condiciones: " + " · ".join(cond))
    if pedido.get("comentario_admin"):
        st.caption(f"Observación: {pedido['comentario_admin']}")

    items = repo.listar_items(pedido["id"])
    if items:
        df = pd.DataFrame(items)
        cols = {
            "codigo": "Código",
            "descripcion": "Descripción",
            "unidades_ajustadas_admin": "Unid. finales",
            "precio_final_acordado": "Precio final",
            "total": "Total",
            "comentario_admin": "Observación",
        }
        for c in cols:
            if c not in df.columns:
                df[c] = None
        st.dataframe(
            df[list(cols.keys())].rename(columns=cols), width="stretch", hide_index=True
        )
    _boton_pdf(pedido, provs)

    if pedido["estado"] != "cerrado":  # pedidos heredados
        if st.button("✅ Cerrar pedido", type="primary"):
            repo.cambiar_estado(pedido["id"], "cerrado")
            st.rerun()


# ----------------------------------------------------------------------
# Entrada
# ----------------------------------------------------------------------
def render(usuario: dict) -> None:
    ui.encabezado("Administrador")
    if "pedido_admin_id" in st.session_state:
        _detalle(st.session_state["pedido_admin_id"])
        return

    seccion = st.sidebar.radio("Menú", ["Bandeja", "Tablero / búsqueda"])
    if seccion == "Bandeja":
        _bandeja()
    else:
        vista_tablero.render(usuario)
