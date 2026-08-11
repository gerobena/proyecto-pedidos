"""Genera el PDF del pedido: documento con lo acordado con el proveedor."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fpdf import FPDF

_LOGO = Path(__file__).resolve().parents[2] / "app" / "logo.jpg"


def _s(v) -> str:
    """Texto seguro para las fuentes base de fpdf (latin-1)."""
    if v is None:
        return ""
    return str(v).encode("latin-1", "replace").decode("latin-1")


def _money(v) -> str:
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return "-"


def _unidades(v) -> str:
    try:
        return f"{float(v):g}"
    except (TypeError, ValueError):
        return ""


def pedido_pdf(pedido: dict, items: list[dict], proveedor: str) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    if _LOGO.exists():
        pdf.image(str(_LOGO), x=10, y=8, w=45)
        pdf.set_y(32)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, "Importadora JDG - Just Durable Goods Import",
             new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _s(f"Pedido {pedido.get('numero_pedido', '')}"),
             new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _s(f"Proveedor: {proveedor}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, _s(f"Fecha de la cita: {pedido.get('fecha_cita') or '-'}"),
             new_x="LMARGIN", new_y="NEXT")
    cond = []
    if pedido.get("dias_credito"):
        cond.append(f"{pedido['dias_credito']} dias de credito")
    if pedido.get("descuento_pct"):
        cond.append(f"{pedido['descuento_pct']:.1f}% de descuento")
    pdf.cell(0, 6, _s("Condiciones: " + (", ".join(cond) if cond else "-")),
             new_x="LMARGIN", new_y="NEXT")
    if pedido.get("comentario_admin"):
        pdf.multi_cell(0, 6, _s(f"Observacion: {pedido['comentario_admin']}"))
    pdf.ln(2)

    # Filas y total
    total_general = 0.0
    filas = []
    for it in items:
        unidades = it.get("unidades_ajustadas_admin")
        if unidades is None:
            unidades = it.get("unidades_sugeridas_tienda")
        try:
            if unidades is not None and float(unidades) == 0:
                continue  # el admin decidió no pedir este producto
        except (TypeError, ValueError):
            pass
        precio = it.get("precio_final_acordado")
        if precio is None:
            precio = it.get("precio_proveedor")
        tot = it.get("total")
        if tot is None and unidades not in (None, "") and precio not in (None, ""):
            tot = float(unidades) * float(precio)
        total_general += float(tot or 0)
        filas.append((it.get("codigo"), it.get("descripcion"), unidades, precio, tot))

    pdf.set_font("Helvetica", "", 9)
    with pdf.table(
        col_widths=(18, 92, 15, 25, 25),
        text_align=("LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT"),
    ) as table:
        hdr = table.row()
        for h in ("Codigo", "Descripcion", "Unid.", "Precio final", "Total"):
            hdr.cell(h)
        for cod, desc, un, pr, tot in filas:
            row = table.row()
            row.cell(_s(cod))
            row.cell(_s(desc))
            row.cell(_unidades(un))
            row.cell(_money(pr))
            row.cell(_money(tot))

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, _s(f"Total del pedido: $ {total_general:,.2f}"),
             new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 6, _s(f"Generado el {date.today().isoformat()}. "
                      "Precios incluyen IVA cuando aplica."),
             new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
