# exporter.py ── Exportaciones CSV y PDF (piramide)

from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Polygon, String
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

import services
from models import RawMaterial, Formula

# ---------------------------------------------------------------------------#
# CSV
# ---------------------------------------------------------------------------#
def export_materials_csv(path: Path):
    headers = ["id", "name", "category", "cost_per_g", "inventory_g", "ifra_limit_pct"]
    rows: List[RawMaterial] = services.list_all(RawMaterial)
    with path.open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(headers)
        for rm in rows:
            wr.writerow([getattr(rm, h) for h in headers])


def export_formulas_csv(path: Path):
    headers = ["id", "name", "category", "total_weight_g", "cost_estimate"]
    rows: List[Formula] = services.list_formulas()
    with path.open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(headers)
        for fo in rows:
            rev = fo.latest()
            wr.writerow([fo.id, fo.name, fo.category, rev.total_weight(), rev.cost_estimate()])


# ---------------------------------------------------------------------------#
# PDF tabla simple
# ---------------------------------------------------------------------------#
def _draw_table(c: canvas.Canvas, headers, data, x=40, y=780, line_h=16):
    c.setFont("Helvetica-Bold", 10)
    for ix, h in enumerate(headers):
        c.drawString(x + ix * 90, y, h)
    y -= line_h
    c.setFont("Helvetica", 9)
    for row in data:
        for ix, cell in enumerate(row):
            c.drawString(x + ix * 90, y, str(cell))
        y -= line_h
        if y < 40:
            c.showPage()
            y = 780
    c.showPage()


def export_materials_pdf(path: Path):
    rows = services.list_all(RawMaterial)
    data = [[rm.id, rm.name, rm.category, rm.cost_per_g] for rm in rows]
    c = canvas.Canvas(str(path), pagesize=A4)
    _draw_table(c, ["ID", "Nombre", "Categoría", "€/g"], data)
    c.save()


# ---------------------------------------------------------------------------#
# Pirámide olfativa
# ---------------------------------------------------------------------------#
def export_formula_pyramid_pdf(formula: Formula, path: Path):
    width, height = 300, 500
    d = Drawing(width, height)
    colors = ("#f9d423", "#f56991", "#8e44ad")
    levels = {"top": [], "middle": [], "base": []}
    for e in formula.entries:
        levels[e.raw_material.fragrance_pyramid_level.value].append(e.raw_material.name)

    y0 = 450
    for i, (lvl, names) in enumerate(levels.items()):
        d.add(
            Polygon(
                points=[
                    150 - (i + 1) * 60,
                    y0 - i * 120,
                    150 + (i + 1) * 60,
                    y0 - i * 120,
                    150,
                    y0 - (i + 1) * 120,
                ],
                fillColor=colors[i],
                strokeColor="#333333",
            )
        )
        txt = ", ".join(names) if names else "-"
        d.add(String(150, y0 - i * 120 - 40, txt, textAnchor="middle"))

    renderPDF.drawToFile(d, str(path))
