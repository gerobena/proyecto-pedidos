import sys
from pathlib import Path

import streamlit as st

# Permite importar `src.pedidos...` al correr con `streamlit run app/app.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pedidos import vista_admin, vista_tienda  # noqa: E402
from src.pedidos.auth import cerrar_sesion, requerir_login  # noqa: E402

st.set_page_config(page_title="Pedidos JDG", page_icon="📦", layout="wide")

_LOGO = Path(__file__).resolve().parent / "logo.jpg"


def _logo_barra() -> None:
    """Logo grande a todo el ancho de la barra lateral (igual en todas las páginas)."""
    if _LOGO.exists():
        st.sidebar.image(str(_LOGO), width="stretch")


_logo_barra()
usuario = requerir_login()

with st.sidebar:
    st.divider()
    st.markdown(f"**{usuario.get('nombre') or usuario['email']}**")
    st.caption(f"Rol: {usuario['rol']}")
    if st.button("Cerrar sesión"):
        cerrar_sesion()
        st.rerun()
    st.divider()

if usuario["rol"] == "administrador":
    vista_admin.render(usuario)
else:
    vista_tienda.render(usuario)
