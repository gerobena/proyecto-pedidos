"""Conexión a Supabase.

Centraliza la creación del cliente de Supabase leyendo las credenciales de
`.streamlit/secrets.toml`. Funciona igual dentro de Streamlit o en un script
suelto (como la prueba de conexión).
"""
from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

from supabase import Client, create_client

# Raíz del proyecto (dos niveles arriba de este archivo: src/pedidos/db.py)
ROOT = Path(__file__).resolve().parents[2]
SECRETS_PATH = ROOT / ".streamlit" / "secrets.toml"


def _cargar_credenciales() -> dict:
    """Devuelve el bloque [supabase] de las credenciales.

    Prefiere los secrets de Streamlit si la app corre dentro de Streamlit;
    si no, lee el archivo .streamlit/secrets.toml directamente.
    """
    try:
        import streamlit as st

        if hasattr(st, "secrets") and "supabase" in st.secrets:
            return dict(st.secrets["supabase"])
    except Exception:
        pass  # No estamos dentro de Streamlit; leemos el archivo.

    if not SECRETS_PATH.exists():
        raise FileNotFoundError(
            f"No encuentro las credenciales en {SECRETS_PATH}. "
            "Copia .streamlit/secrets.toml.example a .streamlit/secrets.toml "
            "y llena los valores de Supabase."
        )
    with open(SECRETS_PATH, "rb") as f:
        return tomllib.load(f)["supabase"]


@lru_cache(maxsize=1)
def get_client() -> Client:
    """Cliente de Supabase con permisos de servidor (secret key).

    Se usa desde el backend de la app (Streamlit corre del lado del servidor),
    nunca se expone la secret key al navegador. Lee y escribe las tablas.
    """
    cred = _cargar_credenciales()
    return create_client(cred["url"], cred["secret_key"])


@lru_cache(maxsize=1)
def get_auth_client() -> Client:
    """Cliente de Supabase con la publishable key.

    Se usa solo para el inicio de sesión de usuarios (Supabase Auth). No tiene
    permisos sobre las tablas: la autorización real la da el rol en `perfiles`.
    """
    cred = _cargar_credenciales()
    return create_client(cred["url"], cred["publishable_key"])
