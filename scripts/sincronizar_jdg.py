"""Copia los parquets que la app de pedidos necesita desde el panel JDG.

Versión local/manual de lo que hará la GitHub Action (Fase 5). Copia
summary.parquet y rendimiento.parquet del proyecto JDG a data/.

Uso:
    .venv\\Scripts\\python.exe scripts\\sincronizar_jdg.py
    (opcional) pasar la carpeta origen:  ... scripts\\sincronizar_jdg.py <ruta_data_jdg>
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

DESTINO = Path(__file__).resolve().parents[1] / "data"
ARCHIVOS = ["summary.parquet", "rendimiento.parquet"]

# Origen: argumento -> variable de entorno -> ruta por defecto del proyecto JDG.
_DEFECTO = r"D:/Jupyter_Notebooks/proyecto-jdg/data"


def main() -> int:
    origen = Path(
        sys.argv[1] if len(sys.argv) > 1 else os.environ.get("JDG_DATA_DIR", _DEFECTO)
    )
    if not origen.exists():
        print(f"❌ No existe la carpeta de origen: {origen}")
        return 1

    DESTINO.mkdir(exist_ok=True)
    for a in ARCHIVOS:
        o = origen / a
        if not o.exists():
            print(f"❌ Falta {o}")
            return 1
        shutil.copy2(o, DESTINO / a)
        print(f"✅ Copiado {a}")
    print(f"Listo. Parquets de JDG sincronizados en {DESTINO}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
