"""Utilidades pequeñas compartidas por las vistas."""
from __future__ import annotations

import math


def txt(v) -> str | None:
    """Normaliza un texto: None o cadena vacía -> None."""
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def num(v) -> float | None:
    """Convierte a float; None o vacío o NaN -> None."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f
