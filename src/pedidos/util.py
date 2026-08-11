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


def iguales(a, b, tol: float = 1e-6) -> bool:
    """Compara dos valores (numéricos con tolerancia, o texto)."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        return abs(float(a) - float(b)) < tol
    except (TypeError, ValueError):
        return str(a) == str(b)
