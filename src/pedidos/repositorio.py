"""Repositorio: todas las lecturas y escrituras a la base de datos.

La interfaz (Streamlit) llama a estas funciones y nunca habla con Supabase
directamente. Así la lógica de datos vive en un solo lugar. Todas las consultas
pasan por `ejecutar`, que reintenta ante fallos de red transitorios.
"""
from __future__ import annotations

from datetime import date

from .db import ejecutar, get_client

# ----------------------------------------------------------------------
# Proveedores
# ----------------------------------------------------------------------
def listar_proveedores() -> list[dict]:
    return ejecutar(
        get_client().table("proveedores").select("*").order("nombre")
    ).data


def crear_proveedor(
    nombre: str, ruc: str | None = None, dias_credito_habitual: int | None = None
) -> dict:
    fila: dict = {"nombre": nombre}
    if ruc:
        fila["ruc"] = ruc
    if dias_credito_habitual is not None:
        fila["dias_credito_habitual"] = dias_credito_habitual
    return ejecutar(get_client().table("proveedores").insert(fila)).data[0]


def obtener_o_crear_proveedor(nombre: str) -> dict:
    """Devuelve el proveedor por nombre; si no existe en la tabla local, lo crea."""
    nombre = nombre.strip()
    res = ejecutar(
        get_client().table("proveedores").select("*").eq("nombre", nombre).limit(1)
    )
    return res.data[0] if res.data else crear_proveedor(nombre)


# ----------------------------------------------------------------------
# Pedidos (cabecera)
# ----------------------------------------------------------------------
def crear_pedido(proveedor_id: int, fecha_cita: date | None, responsable: str) -> dict:
    """Crea la cabecera en estado 'sugerido'. Devuelve el pedido con su número."""
    fila: dict = {"proveedor_id": proveedor_id, "responsable": responsable}
    if fecha_cita:
        fila["fecha_cita"] = fecha_cita.isoformat()
    return ejecutar(get_client().table("pedidos").insert(fila)).data[0]


def obtener_pedido(pedido_id: int) -> dict | None:
    res = ejecutar(
        get_client().table("pedidos").select("*").eq("id", pedido_id).limit(1)
    )
    return res.data[0] if res.data else None


def listar_pedidos(estados: list[str] | None = None) -> list[dict]:
    q = get_client().table("pedidos").select("*").order("creado_en", desc=True)
    if estados:
        q = q.in_("estado", estados)
    return ejecutar(q).data


def actualizar_cabecera(pedido_id: int, campos: dict) -> None:
    ejecutar(get_client().table("pedidos").update(campos).eq("id", pedido_id))


def cambiar_estado(pedido_id: int, nuevo: str) -> None:
    ejecutar(get_client().table("pedidos").update({"estado": nuevo}).eq("id", pedido_id))


def eliminar_pedido(pedido_id: int) -> None:
    """Borra el pedido y sus líneas (cascada)."""
    ejecutar(get_client().table("pedidos").delete().eq("id", pedido_id))


# ----------------------------------------------------------------------
# Ítems (líneas del pedido)
# ----------------------------------------------------------------------
def listar_items(pedido_id: int) -> list[dict]:
    return ejecutar(
        get_client()
        .table("pedido_items")
        .select("*")
        .eq("pedido_id", pedido_id)
        .order("id")
    ).data


def reemplazar_items(pedido_id: int, filas: list[dict]) -> None:
    """Borra los ítems actuales del pedido y guarda la lista nueva."""
    db = get_client()
    ejecutar(db.table("pedido_items").delete().eq("pedido_id", pedido_id))
    if filas:
        for f in filas:
            f["pedido_id"] = pedido_id
        ejecutar(db.table("pedido_items").insert(filas))


def actualizar_item(item_id: int, campos: dict) -> None:
    ejecutar(get_client().table("pedido_items").update(campos).eq("id", item_id))
