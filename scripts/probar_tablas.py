"""Verifica que las tablas del esquema inicial existen y son accesibles."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pedidos.db import get_client  # noqa: E402

TABLAS = ["proveedores", "pedidos", "pedido_items"]


def main() -> int:
    client = get_client()
    print("Revisando tablas...\n")
    ok = True
    for tabla in TABLAS:
        try:
            res = client.table(tabla).select("*", count="exact").execute()
            print(f"  ✅ {tabla:<14} accesible — filas: {res.count}")
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f"  ❌ {tabla:<14} error: {type(e).__name__}: {e}")

    if ok:
        print("\n✅ Las tres tablas existen y responden.")
    else:
        print("\n❌ Alguna tabla falló (ver arriba).")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
