"""Conexión a Supabase.

Centraliza la creación del cliente de Supabase leyendo las credenciales de
`.streamlit/secrets.toml`. Funciona igual dentro de Streamlit o en un script
suelto (como la prueba de conexión).
"""
from __future__ import annotations

import time
import tomllib
from functools import lru_cache
from pathlib import Path

import httpx
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


def _endurecer(client: Client) -> None:
    """Reconstruye la sesión de PostgREST sin HTTP/2 y sin reusar conexiones.

    Evita de raíz el `RemoteProtocolError (ConnectionTerminated)` intermitente:
    con HTTP/2 el servidor cierra conexiones keep-alive y la siguiente consulta
    que las reusa falla. Aquí cada consulta abre una conexión nueva (HTTP/1.1).
    """
    try:
        sess = client.postgrest.session
        client.postgrest.session = httpx.Client(
            base_url=sess.base_url,
            headers=sess.headers,
            timeout=sess.timeout,
            http2=False,  # evita el ConnectionTerminated de HTTP/2
            # keep-alive corto: cierra conexiones ociosas antes de que el
            # servidor las mate (y el reintento cubre el caso raro restante).
            limits=httpx.Limits(max_keepalive_connections=10, keepalive_expiry=5.0),
            follow_redirects=True,
        )
    except Exception:  # noqa: BLE001 — si cambia la interna, seguimos sin endurecer
        pass


@lru_cache(maxsize=1)
def get_client() -> Client:
    """Cliente de Supabase con permisos de servidor (secret key).

    Se usa desde el backend de la app (Streamlit corre del lado del servidor),
    nunca se expone la secret key al navegador. Lee y escribe las tablas.
    """
    cred = _cargar_credenciales()
    client = create_client(cred["url"], cred["secret_key"])
    _endurecer(client)
    return client


@lru_cache(maxsize=1)
def get_auth_client() -> Client:
    """Cliente de Supabase con la publishable key.

    Se usa solo para el inicio de sesión de usuarios (Supabase Auth). No tiene
    permisos sobre las tablas: la autorización real la da el rol en `perfiles`.
    """
    cred = _cargar_credenciales()
    return create_client(cred["url"], cred["publishable_key"])


def ejecutar(query, intentos: int = 3):
    """Ejecuta una consulta de Supabase reintentando ante fallos de red transitorios.

    supabase-py usa httpx con HTTP/2; a veces el servidor cierra una conexión
    keep-alive en reposo y la siguiente consulta falla con RemoteProtocolError /
    ConnectError. Reintentar (con una conexión nueva) lo resuelve.
    """
    ultimo: Exception | None = None
    for i in range(intentos):
        try:
            return query.execute()
        except httpx.TransportError as e:  # conexión/protocolo (no errores HTTP 4xx/5xx)
            ultimo = e
            time.sleep(0.3 * (i + 1))
    raise ultimo  # type: ignore[misc]
