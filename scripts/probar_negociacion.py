"""Prueba: el admin ajusta precio final y agrega un producto en la negociación."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pedidos import repositorio as repo  # noqa: E402
from src.pedidos.db import get_client  # noqa: E402


def main() -> int:
    prov = repo.listar_proveedores()[0]

    # Tienda: un producto sugerido a la oferta del proveedor.
    pedido = repo.crear_pedido(prov["id"], date.today(), "tienda@jdg.local")
    repo.reemplazar_items(
        pedido["id"],
        [{"codigo": "P1", "descripcion": "Producto original",
          "unidades_sugeridas_tienda": 10, "precio_proveedor": 3.00, "iva_aplica": True}],
    )
    repo.cambiar_estado(pedido["id"], "en_analisis")

    # Admin negocia: sube a 15 unidades, cierra precio final 2.70, y AGREGA un
    # producto nuevo (5 unidades a 4.00) para mejorar el descuento por volumen.
    repo.reemplazar_items(
        pedido["id"],
        [
            {"codigo": "P1", "descripcion": "Producto original",
             "unidades_sugeridas_tienda": 10, "unidades_ajustadas_admin": 15,
             "precio_proveedor": 3.00, "precio_final_acordado": 2.70,
             "iva_aplica": True, "total": round(15 * 2.70, 2)},
            {"codigo": "P2", "descripcion": "Producto agregado por admin",
             "unidades_ajustadas_admin": 5, "precio_final_acordado": 4.00,
             "iva_aplica": True, "total": 20.0},
        ],
    )

    items = repo.listar_items(pedido["id"])
    print(f"Pedido {pedido['numero_pedido']} — líneas: {len(items)}")
    for it in items:
        print(f"  - {it['codigo']} {it['descripcion']}: "
              f"finales={it['unidades_ajustadas_admin']}, "
              f"precio_final={it['precio_final_acordado']}, total={it['total']}")
    assert len(items) == 2
    assert any(it["codigo"] == "P2" for it in items)
    assert any(it["precio_final_acordado"] == 2.70 for it in items)
    print("✅ Ajuste de precio final + producto agregado OK")

    get_client().table("pedidos").delete().eq("id", pedido["id"]).execute()
    print("🧹 Pedido de prueba borrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
