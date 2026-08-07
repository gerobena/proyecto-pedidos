"""Panel de apoyo con datos de JDG para los códigos de un pedido."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from . import jdg


def panel(codigos) -> None:
    """Muestra rotación, antigüedad, margen, GMROI y acción de cada código."""
    if not jdg.disponible():
        st.info(
            "Datos de JDG no disponibles. Corre `scripts/sincronizar_jdg.py` "
            "para traer los parquets del panel."
        )
        return

    df = jdg.buscar(codigos)
    if df.empty:
        st.caption("Escribe códigos válidos para ver su análisis de JDG.")
        return

    vista = pd.DataFrame(
        {
            "Código": df["CODIGO"],
            "Producto": df.get("PRODUCTO"),
            "Últ. compra": df.get("FECHA_ULT_COMPRA"),
            "Costo últ. c/IVA": df.get("COSTO_ULT_COMPRA_CON_IVA"),
            "¿IVA?": df.get("GRAVA_IVA"),
            "Stock": df.get("STOCK"),
            "Antig. días": df.get("ANTIGUEDAD_STOCK_DIAS"),
            "Cobertura días": df.get("COBERTURA_DIAS"),
            "Rotación": df.get("ROTACION"),
            "Margen %": df.get("margen_bruto_%"),
            "GMROI": df.get("GMROI"),
            "Acción": df.get("ACCION"),
            "Proveedor": df.get("PROVEEDOR"),
        }
    )
    st.dataframe(
        vista,
        width="stretch",
        hide_index=True,
        column_config={
            "Últ. compra": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "Costo últ. c/IVA": st.column_config.NumberColumn(format="%.2f"),
            "¿IVA?": st.column_config.CheckboxColumn(),
            "Margen %": st.column_config.NumberColumn(format="%.1f"),
            "GMROI": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.caption(
        "Costo de la última compra (con IVA cuando el producto grava, dato real "
        "de la factura). Rotación, antigüedad, GMROI y acción vienen del panel JDG."
    )
