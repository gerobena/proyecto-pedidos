"""Prueba: la tienda teclea solo el código y JDG llena descripción y último precio."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from src.pedidos import repositorio as repo  # noqa: E402
from src.pedidos import vista_tienda  # noqa: E402
from src.pedidos.db import get_client  # noqa: E402


def main() -> int:
    prov = repo.listar_proveedores()[0]
    pedido = repo.crear_pedido(prov["id"], date.today(), "tienda@jdg.local")

    # La tienda solo pone el código y unidades; descripción y precio en blanco.
    df = pd.DataFrame(
        [
            {
                "codigo": "1001",
                "descripcion": None,
                "unidades_sugeridas_tienda": 5,
                "ultimo_precio_compra_sistema": None,
                "precio_proveedor": 10.0,
                "iva_aplica": True,
                "observacion_tienda": None,
            }
        ]
    )
    vista_tienda._guardar_items(pedido["id"], df)

    it = repo.listar_items(pedido["id"])[0]
    print(f"codigo: {it['codigo']}")
    print(f"descripcion (autocompletada): {it['descripcion']}")
    print(f"ultimo_precio_compra_sistema (de JDG, s/IVA): {it['ultimo_precio_compra_sistema']}")
    assert it["descripcion"] and "CORTADOR" in it["descripcion"]
    assert it["ultimo_precio_compra_sistema"] is not None
    print("✅ Autocompletado desde JDG OK")

    get_client().table("pedidos").delete().eq("id", pedido["id"]).execute()
    print("🧹 Pedido de prueba borrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
