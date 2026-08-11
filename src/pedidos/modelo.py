"""Reglas del pedido: estados y transiciones permitidas.

Es la "máquina de estados". La base de datos ya restringe los valores posibles
(CHECK); aquí definimos además a qué estado puede pasar cada uno, para que la
interfaz solo ofrezca movimientos válidos.
"""
from __future__ import annotations

ESTADOS = ["sugerido", "en_analisis", "cerrado"]

ETIQUETA_ESTADO = {
    "sugerido": "📝 Sugerido",
    "en_analisis": "🔎 En análisis",
    "cerrado": "✅ Cerrado",
    # Estados heredados (pedidos antiguos); ya no se usan en el flujo.
    "enviado": "📤 Enviado",
    "facturado": "🧾 Facturado",
}

# A qué estados se puede mover cada estado.
TRANSICIONES = {
    "sugerido": ["en_analisis"],
    "en_analisis": ["cerrado", "sugerido"],  # cerrar, o devolver a tienda
    "cerrado": [],
}


def etiqueta(estado: str) -> str:
    return ETIQUETA_ESTADO.get(estado, estado)


def puede_transicionar(actual: str, nuevo: str) -> bool:
    return nuevo in TRANSICIONES.get(actual, [])
