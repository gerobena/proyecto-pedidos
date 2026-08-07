"""Lectura de los datos del panel JDG para autocompletar y apoyar la decisión.

Lee, en **solo lectura**, los parquets `summary.parquet` y `rendimiento.parquet`
que el panel JDG genera. En local se copian a `data/` con
`scripts/sincronizar_jdg.py`; en producción los dejará ahí la GitHub Action
(Fase 5). Todo lo de JDG es SIN IVA (regla del panel).
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"

_SUMMARY = DATA / "summary.parquet"
_RENDIMIENTO = DATA / "rendimiento.parquet"

# Columnas que tomamos de cada parquet.
_COLS_SUMMARY = [
    "CODIGO",
    "PRODUCTO",
    "CATEGORIA",
    "MARCA",
    "COSTO",
    "FECHA_ULT_COMPRA",
    "COSTO_ULT_COMPRA_SIN_IVA",
    "COSTO_ULT_COMPRA_CON_IVA",
    "GRAVA_IVA",
    "STOCK",
    "COBERTURA_DIAS",
    "ANTIGUEDAD_STOCK_DIAS",
    "ROTACION",
    "margen_bruto_%",
    "unidades_vendidas_totales",
]
_COLS_RENDIMIENTO = ["CODIGO", "ACCION", "GMROI", "PROVEEDOR"]


def disponible() -> bool:
    return _SUMMARY.exists() and _RENDIMIENTO.exists()


def _f(v) -> float | None:
    """float o None si es NaN/None."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _b(v) -> bool | None:
    """bool o None si el dato falta."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return bool(v)


@lru_cache(maxsize=1)
def _cargar() -> pd.DataFrame:
    summary = pd.read_parquet(_SUMMARY)
    rend = pd.read_parquet(_RENDIMIENTO)
    s = summary[[c for c in _COLS_SUMMARY if c in summary.columns]].copy()
    r = rend[[c for c in _COLS_RENDIMIENTO if c in rend.columns]].copy()
    df = s.merge(r, on="CODIGO", how="left")
    df["CODIGO"] = df["CODIGO"].astype(str).str.strip()
    return df


def info(codigo: str | None) -> dict | None:
    """Datos de JDG para un código, o None si no existe / no hay datos."""
    if not disponible() or not codigo:
        return None
    df = _cargar()
    fila = df[df["CODIGO"] == str(codigo).strip()]
    if fila.empty:
        return None
    r = fila.iloc[0]
    return {
        "codigo": r["CODIGO"],
        "descripcion": r.get("PRODUCTO"),
        # Último precio de compra (de la última factura real):
        "ultimo_precio_con_iva": _f(r.get("COSTO_ULT_COMPRA_CON_IVA")),
        "ultimo_precio_sin_iva": _f(r.get("COSTO_ULT_COMPRA_SIN_IVA")),
        "grava_iva": _b(r.get("GRAVA_IVA")),
        "fecha_ult_compra": r.get("FECHA_ULT_COMPRA"),
        "costo_valuacion": _f(r.get("COSTO")),  # costo de valuación (SIN IVA)
        "stock": _f(r.get("STOCK")),
        "antiguedad_dias": _f(r.get("ANTIGUEDAD_STOCK_DIAS")),
        "cobertura_dias": _f(r.get("COBERTURA_DIAS")),
        "rotacion": r.get("ROTACION"),
        "margen_pct": _f(r.get("margen_bruto_%")),
        "accion": r.get("ACCION"),
        "gmroi": _f(r.get("GMROI")),
        "proveedor": r.get("PROVEEDOR"),
    }


def buscar(codigos) -> pd.DataFrame:
    """Filas de JDG para una lista de códigos (para el panel de apoyo)."""
    if not disponible():
        return pd.DataFrame()
    df = _cargar()
    cods = [str(c).strip() for c in codigos if str(c).strip()]
    return df[df["CODIGO"].isin(cods)]


def proveedores() -> list[str]:
    """Nombres de proveedores conocidos por JDG (para elegir sin re-crear)."""
    if not disponible():
        return []
    df = _cargar()
    if "PROVEEDOR" not in df.columns:
        return []
    s = df["PROVEEDOR"].dropna().astype(str).str.strip()
    s = s[s != ""]
    return sorted(s.unique().tolist())


def completar(
    codigo: str | None,
    descripcion: str | None,
    ultimo_precio: float | None,
    iva: bool | None,
) -> tuple[str | None, float | None, bool | None]:
    """Autocompleta desde JDG lo que falte y define el IVA del producto.

    - Descripción: se rellena si está vacía.
    - Último precio: se rellena (si está vacío) con el costo de la última
      compra CON IVA (que ya iguala al sin IVA cuando el producto no grava).
    - IVA: si el producto está en JDG, su flag `GRAVA_IVA` manda (es el dato
      real de las facturas), así que sobrescribe la casilla.
    """
    d = info(codigo)
    if not d:
        return descripcion, ultimo_precio, iva
    if not descripcion:
        descripcion = d.get("descripcion")
    if ultimo_precio is None:
        ultimo_precio = d.get("ultimo_precio_con_iva")
    if d.get("grava_iva") is not None:
        iva = d.get("grava_iva")
    return descripcion, ultimo_precio, iva
