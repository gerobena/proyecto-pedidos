"""Prueba de humo del flujo completo: tienda -> análisis admin -> enviado."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pedidos import repositorio as repo  # noqa: E402
from src.pedidos.db import get_client  # noqa: E402


def main() -> int:
    prov = repo.listar_proveedores()[0]

    # 1) Tienda crea el pedido y el sugerido.
    pedido = repo.crear_pedido(prov["id"], date.today(), "tienda@jdg.local")
    repo.reemplazar_items(
        pedido["id"],
        [
            {"codigo": "X1", "descripcion": "Item A",
             "unidades_sugeridas_tienda": 10, "precio_proveedor": 3.0, "total": 30.0},
        ],
    )
    repo.cambiar_estado(pedido["id"], "en_analisis")
    print(f"1) Tienda envió {pedido['numero_pedido']} -> en_analisis")

    # 2) Admin ajusta la línea y las condiciones.
    item = repo.listar_items(pedido["id"])[0]
    repo.actualizar_item(item["id"], {"unidades_ajustadas_admin": 6,
                                      "comentario_admin": "bajar por rotación lenta"})
    repo.actualizar_cabecera(pedido["id"], {"dias_credito": 60, "descuento_pct": 5.0,
                                            "comentario_admin": "60 días y 5% acordado"})
    repo.cambiar_estado(pedido["id"], "enviado")

    # 3) Verificar.
    p = repo.obtener_pedido(pedido["id"])
    it = repo.listar_items(pedido["id"])[0]
    print(f"2) Admin: sugeridas={it['unidades_sugeridas_tienda']} -> "
          f"ajustadas={it['unidades_ajustadas_admin']}, comentario='{it['comentario_admin']}'")
    print(f"3) Cabecera: estado={p['estado']}, credito={p['dias_credito']}d, "
          f"descuento={p['descuento_pct']}%")
    assert p["estado"] == "enviado" and it["unidades_ajustadas_admin"] == 6
    print("✅ Flujo tienda->admin->enviado OK")

    get_client().table("pedidos").delete().eq("id", pedido["id"]).execute()
    print("🧹 Pedido de prueba borrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
