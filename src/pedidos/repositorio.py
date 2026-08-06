"""Repositorio: todas las lecturas y escrituras a la base de datos.

La interfaz (Streamlit) llama a estas funciones y nunca habla con Supabase
directamente. Así la lógica de datos vive en un solo lugar.
"""
from __future__ import annotations

from datetime import date

from .db import get_client

# ----------------------------------------------------------------------
# Proveedores
# ----------------------------------------------------------------------
def listar_proveedores() -> list[dict]:
    return (
        get_client()
        .table("proveedores")
        .select("*")
        .order("nombre")
        .execute()
        .data
    )


def crear_proveedor(
    nombre: str, ruc: str | None = None, dias_credito_habitual: int | None = None
) -> dict:
    fila: dict = {"nombre": nombre}
    if ruc:
        fila["ruc"] = ruc
    if dias_credito_habitual is not None:
        fila["dias_credito_habitual"] = dias_credito_habitual
    return get_client().table("proveedores").insert(fila).execute().data[0]


# ----------------------------------------------------------------------
# Pedidos (cabecera)
# ----------------------------------------------------------------------
def crear_pedido(
    proveedor_id: int, fecha_cita: date | None, responsable: str
) -> dict:
    """Crea la cabecera en estado 'sugerido'. Devuelve el pedido con su número."""
    fila: dict = {"proveedor_id": proveedor_id, "responsable": responsable}
    if fecha_cita:
        fila["fecha_cita"] = fecha_cita.isoformat()
    return get_client().table("pedidos").insert(fila).execute().data[0]


def obtener_pedido(pedido_id: int) -> dict | None:
    res = (
        get_client()
        .table("pedidos")
        .select("*")
        .eq("id", pedido_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def listar_pedidos(estados: list[str] | None = None) -> list[dict]:
    q = get_client().table("pedidos").select("*").order("creado_en", desc=True)
    if estados:
        q = q.in_("estado", estados)
    return q.execute().data


def actualizar_cabecera(pedido_id: int, campos: dict) -> None:
    get_client().table("pedidos").update(campos).eq("id", pedido_id).execute()


def cambiar_estado(pedido_id: int, nuevo: str) -> None:
    get_client().table("pedidos").update({"estado": nuevo}).eq(
        "id", pedido_id
    ).execute()


# ----------------------------------------------------------------------
# Ítems (líneas del pedido)
# ----------------------------------------------------------------------
def listar_items(pedido_id: int) -> list[dict]:
    return (
        get_client()
        .table("pedido_items")
        .select("*")
        .eq("pedido_id", pedido_id)
        .order("id")
        .execute()
        .data
    )


def reemplazar_items(pedido_id: int, filas: list[dict]) -> None:
    """Borra los ítems actuales del pedido y guarda la lista nueva.

    Sencillo y predecible para el volumen que manejamos (pocas líneas por
    pedido). Cada fila es un dict con las columnas de pedido_items.
    """
    db = get_client()
    db.table("pedido_items").delete().eq("pedido_id", pedido_id).execute()
    if filas:
        for f in filas:
            f["pedido_id"] = pedido_id
        db.table("pedido_items").insert(filas).execute()


def actualizar_item(item_id: int, campos: dict) -> None:
    get_client().table("pedido_items").update(campos).eq("id", item_id).execute()
