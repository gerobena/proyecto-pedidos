"""Crea un usuario de la app: cuenta en Supabase Auth + perfil con rol.

Lo corre el administrador, una vez por persona. Pide la contraseña de forma
oculta (no se guarda en ningún lado, la maneja Supabase).

Uso (desde la carpeta del proyecto):
    .venv\\Scripts\\python.exe scripts\\crear_usuario.py
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pedidos.db import get_client  # noqa: E402

ROLES = {"1": "administrador", "2": "tienda"}


def main() -> int:
    db = get_client()
    print("=== Crear usuario de Pedidos JDG ===")
    email = input("Correo: ").strip().lower()
    nombre = input("Nombre: ").strip()
    print("Rol:  1) administrador   2) tienda (responsable)")
    rol = ROLES.get(input("Elige 1 o 2: ").strip())
    if not rol:
        print("❌ Opción de rol inválida.")
        return 1

    p1 = getpass.getpass("Contraseña (mínimo 6 caracteres): ")
    p2 = getpass.getpass("Repite la contraseña: ")
    if p1 != p2:
        print("❌ Las contraseñas no coinciden.")
        return 1
    if len(p1) < 6:
        print("❌ La contraseña es muy corta (mínimo 6).")
        return 1

    try:
        db.auth.admin.create_user(
            {"email": email, "password": p1, "email_confirm": True}
        )
    except Exception as e:  # noqa: BLE001
        print(f"❌ Error creando la cuenta en Auth: {e}")
        return 1

    db.table("perfiles").upsert(
        {"email": email, "nombre": nombre, "rol": rol}, on_conflict="email"
    ).execute()

    print(f"\n✅ Usuario creado: {email}  (rol: {rol})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
