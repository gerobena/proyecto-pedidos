"""Inicio de sesión y roles.

Autenticación con Supabase Auth (publishable key); autorización (rol) desde la
tabla `perfiles`. Incluye el "portón" de login para Streamlit.
"""
from __future__ import annotations

import streamlit as st

from .db import get_auth_client, get_client


def _perfil_de(email: str) -> dict | None:
    """Devuelve {'rol', 'nombre'} del correo, o None si no tiene perfil."""
    db = get_client()
    res = (
        db.table("perfiles")
        .select("rol, nombre")
        .eq("email", email)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def iniciar_sesion(email: str, password: str) -> dict:
    """Valida credenciales y devuelve el usuario con su rol.

    Lanza una excepción si las credenciales son inválidas o si el usuario no
    tiene un perfil/rol asignado.
    """
    auth = get_auth_client()
    resp = auth.auth.sign_in_with_password({"email": email, "password": password})
    correo = resp.user.email
    perfil = _perfil_de(correo)
    if perfil is None:
        raise PermissionError(
            "Este usuario no tiene un rol asignado. Avisa al administrador."
        )
    return {"email": correo, "rol": perfil["rol"], "nombre": perfil.get("nombre")}


def requerir_login() -> dict:
    """Portón de acceso. Si no hay sesión, muestra el login y detiene la app.

    Devuelve el diccionario del usuario {'email', 'rol', 'nombre'}.
    """
    if "usuario" in st.session_state:
        return st.session_state["usuario"]

    st.title("📦 Pedidos JDG")
    st.subheader("Iniciar sesión")
    with st.form("login"):
        email = st.text_input("Correo")
        password = st.text_input("Contraseña", type="password")
        enviar = st.form_submit_button("Entrar")

    if enviar:
        try:
            usuario = iniciar_sesion(email.strip().lower(), password)
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudo iniciar sesión: {e}")
            st.stop()
        st.session_state["usuario"] = usuario
        st.rerun()

    st.stop()


def cerrar_sesion() -> None:
    """Cierra la sesión del usuario actual."""
    st.session_state.pop("usuario", None)
    try:
        get_auth_client().auth.sign_out()
    except Exception:  # noqa: BLE001
        pass
