"""Prueba de humo del repositorio: crea un pedido, le pone ítems, lo lee y lo borra."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pedidos import repositorio as repo  # noqa: E402
from src.pedidos.db import get_client  # noqa: E402


def main() -> int:
    provs = repo.listar_proveedores()
    if not provs:
        print("❌ No hay proveedores. Corre db/001_esquema_inicial.sql primero.")
        return 1
    prov = provs[0]
    print(f"Proveedor de prueba: {prov['nombre']} (id {prov['id']})")

    pedido = repo.crear_pedido(prov["id"], date.today(), responsable="prueba@jdg.local")
    print(f"✅ Pedido creado con número automático: {pedido['numero_pedido']}")
    print(f"   estado inicial: {pedido['estado']}")

    repo.reemplazar_items(
        pedido["id"],
        [
            {
                "codigo": "A001",
                "descripcion": "Producto de prueba 1",
                "unidades_sugeridas_tienda": 10,
                "precio_proveedor": 2.50,
                "iva_aplica": True,
                "total": 25.0,
            },
            {
                "codigo": "B002",
                "descripcion": "Producto de prueba 2",
                "unidades_sugeridas_tienda": 4,
                "precio_proveedor": 8.00,
                "iva_aplica": False,
                "total": 32.0,
            },
        ],
    )
    items = repo.listar_items(pedido["id"])
    print(f"✅ Ítems guardados: {len(items)}")
    for it in items:
        print(f"   - {it['codigo']} {it['descripcion']}: total {it['total']}")

    # Limpieza: borrar el pedido (los ítems caen por cascada).
    get_client().table("pedidos").delete().eq("id", pedido["id"]).execute()
    print("🧹 Pedido de prueba borrado. Base limpia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
