"""Prueba de conexión con Supabase.

Corre este script para confirmar que las credenciales de `.streamlit/secrets.toml`
son correctas y que tu proyecto local se comunica con la base en la nube.

Uso (desde la carpeta del proyecto):
    .venv\\Scripts\\python.exe scripts\\probar_conexion.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Permite importar `src.pedidos...` sin importar desde dónde se ejecute.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pedidos.db import get_client  # noqa: E402


def main() -> int:
    print("Conectando con Supabase...")
    try:
        client = get_client()
        # Llamada ligera al servicio de autenticación: confirma credenciales y
        # red sin necesidad de que existan tablas todavía.
        respuesta = client.auth.admin.list_users()
        usuarios = getattr(respuesta, "users", respuesta)
        n = len(usuarios)
    except Exception as e:  # noqa: BLE001
        print("\n❌ No se pudo conectar.")
        print(f"   Detalle: {type(e).__name__}: {e}")
        print("\n   Revisa que url, publishable_key y secret_key en")
        print("   .streamlit/secrets.toml sean correctos.")
        return 1

    print("\n✅ Conexión exitosa con Supabase.")
    print(f"   Usuarios registrados en Auth: {n}")
    print("   (0 es lo esperado: todavía no hemos creado usuarios.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
