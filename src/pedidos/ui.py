"""Componentes de interfaz compartidos (marca de la app)."""
from __future__ import annotations

import streamlit as st

NAVY = "#181F49"  # azul marino del logo JDG
RED = "#EE1D23"   # rojo del logo JDG


def encabezado(subtitulo: str | None = None) -> None:
    """Título de la página. La marca la da el logo de la barra lateral."""
    seccion = (
        f"<div style='color:#6b7280;font-size:1rem;margin-top:.1rem'>{subtitulo}</div>"
        if subtitulo
        else ""
    )
    st.markdown(
        "<div style='margin:0 0 .6rem 0'>"
        f"<div style='color:{NAVY};font-size:1.9rem;font-weight:900;"
        "letter-spacing:.6px;line-height:1.15'>"
        f"IMPORTADORA <span style='color:{RED}'>JDG</span> - CONTROL DE PEDIDOS</div>"
        f"{seccion}"
        "</div>",
        unsafe_allow_html=True,
    )
