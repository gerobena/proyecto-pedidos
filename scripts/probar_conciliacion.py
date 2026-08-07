"""Prueba del cierre: conciliar factura, marcar discrepancia, facturar y cerrar."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from src.pedidos import repositorio as repo  # noqa: E402
from src.pedidos import vista_admin  # noqa: E402
from src.pedidos.db import get_client  # noqa: E402


def main() -> int:
    prov = repo.listar_proveedores()[0]
    pedido = repo.crear_pedido(prov["id"], date.today(), "tienda@jdg.local")
    repo.reemplazar_items(
        pedido["id"],
        [
            {"codigo": "A", "descripcion": "Item A", "unidades_ajustadas_admin": 10,
             "precio_final_acordado": 2.50},
            {"codigo": "B", "descripcion": "Item B", "unidades_ajustadas_admin": 4,
             "precio_final_acordado": 8.00},
        ],
    )
    repo.cambiar_estado(pedido["id"], "enviado")
    print(f"Pedido {pedido['numero_pedido']} en estado enviado.")

    # Llega la factura: A viene igual (2.50), B viene distinto (8.50 -> discrepancia).
    items = repo.listar_items(pedido["id"])
    df = pd.DataFrame(items).set_index("id")
    df.loc[df["codigo"] == "A", "precio_facturado"] = 2.50
    df.loc[df["codigo"] == "B", "precio_facturado"] = 8.50
    nd = vista_admin._guardar_conciliacion(df)
    print(f"Discrepancias detectadas: {nd}")

    it = {i["codigo"]: i for i in repo.listar_items(pedido["id"])}
    print(f"  A -> facturado {it['A']['precio_facturado']}, discrepancia={it['A']['flag_discrepancia']}")
    print(f"  B -> facturado {it['B']['precio_facturado']}, discrepancia={it['B']['flag_discrepancia']}")
    assert nd == 1
    assert it["A"]["flag_discrepancia"] is False
    assert it["B"]["flag_discrepancia"] is True

    repo.cambiar_estado(pedido["id"], "facturado")
    repo.cambiar_estado(pedido["id"], "cerrado")
    p = repo.obtener_pedido(pedido["id"])
    print(f"Estado final: {p['estado']}")
    assert p["estado"] == "cerrado"
    print("✅ Conciliación + cierre OK")

    get_client().table("pedidos").delete().eq("id", pedido["id"]).execute()
    print("🧹 Pedido de prueba borrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
