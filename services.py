# services.py ── Stock + Versionado de fórmulas + auditoría  (fix eager-load)
# =============================================================================
from __future__ import annotations

import csv
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Sequence

from deepdiff import DeepDiff
from sqlalchemy.orm import Session, selectinload

from models import (
    SessionLocal,
    RawMaterial,
    InventoryMovement,
    Formula,
    FormulaRevision,
    FormulaEntry,
    PyramidLevel,
    AuditLog,
)
from session import current_user

# ---------------------------------------------------------------------------#
# Session helper
# ---------------------------------------------------------------------------#


@contextmanager
def session_scope() -> Iterator[Session]:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


# ---------------------------------------------------------------------------#
# Auditoría
# ---------------------------------------------------------------------------#


def _log(action: str, entity: str, entity_id: int):
    usr = current_user()
    with session_scope() as s:
        s.add(
            AuditLog(
                user_id=usr.id if usr else None,
                action=action,
                entity=entity,
                entity_id=entity_id,
            )
        )


# ---------------------------------------------------------------------------#
# CRUD materias
# ---------------------------------------------------------------------------#


def list_all(model) -> List:
    with session_scope() as s:
        return s.query(model).all()


def create_raw_material(**kwargs):
    with session_scope() as s:
        rm = RawMaterial(**kwargs)
        s.add(rm)
        s.flush()
        _log("create", "RawMaterial", rm.id)


# ---------------------------------------------------------------------------#
# Stock
# ---------------------------------------------------------------------------#


def adjust_stock(raw_material_id: int, delta_g: float, desc=""):
    if delta_g == 0:
        return
    with session_scope() as s:
        rm = s.get(RawMaterial, raw_material_id)
        rm.inventory_g += delta_g
        s.add(
            InventoryMovement(raw_material_id=rm.id, delta_g=delta_g, description=desc)
        )
    _log("stock", "RawMaterial", raw_material_id)


def low_stock_alerts() -> List[RawMaterial]:
    with session_scope() as s:
        return (
            s.query(RawMaterial)
            .filter(RawMaterial.inventory_g < RawMaterial.low_stock_threshold_g)
            .all()
        )


# ---------------------------------------------------------------------------#
# -----------  VERSIONADO DE FÓRMULAS  --------------------------------------
# ---------------------------------------------------------------------------#
def create_formula(name: str, comment: str, entries: Sequence[tuple]):
    with session_scope() as s:
        form = Formula(name=name)
        rev = FormulaRevision(
            number=1, author=current_user().username, comment=comment
        )
        for rm_id, w, dil in entries:
            rev.entries.append(
                FormulaEntry(raw_material_id=rm_id, weight_g=w, dilution=dil)
            )
        form.revisions.append(rev)
        s.add(form)
        s.flush()
        _log("create", "Formula", form.id)
        return form.id


def clone_revision(formula_id: int, comment: str) -> int:
    with session_scope() as s:
        form = s.get(Formula, formula_id)
        base = form.revisions[-1]
        new_rev = FormulaRevision(
            number=base.number + 1,
            author=current_user().username,
            comment=comment,
        )
        for e in base.entries:
            new_rev.entries.append(
                FormulaEntry(
                    raw_material_id=e.raw_material_id,
                    weight_g=e.weight_g,
                    dilution=e.dilution,
                )
            )
        form.revisions.append(new_rev)
        s.add(new_rev)
        s.flush()
        _log("clone", "FormulaRevision", new_rev.id)
        return new_rev.id


def diff_revisions(rev_a_id: int, rev_b_id: int) -> str:
    with session_scope() as s:
        a = s.get(FormulaRevision, rev_a_id)
        b = s.get(FormulaRevision, rev_b_id)

        def dump(rev):
            return {
                e.raw_material.name: {"w": e.weight_g, "dil": e.dilution}
                for e in rev.entries
            }

        diff = DeepDiff(dump(a), dump(b), view="tree")
        return diff.pretty()


def list_formulas() -> List[Formula]:
    """
    Devuelve todas las fórmulas con sus revisiones ya cargadas (evita DetachedInstanceError).
    """
    with session_scope() as s:
        return (
            s.query(Formula)
            .options(selectinload(Formula.revisions))
            .all()
        )


# ---------------------------------------------------------------------------#
# Importación CSV (materias)
# ---------------------------------------------------------------------------#


def import_materials_csv(path: Path) -> dict:
    added = skipped = 0
    with path.open(newline="", encoding="utf-8") as f, session_scope() as s:
        rdr = csv.DictReader(f)
        for row in rdr:
            if s.query(RawMaterial).filter_by(name=row["name"]).first():
                skipped += 1
                continue
            level_str = row.get("fragrance_pyramid_level")
            level = PyramidLevel(level_str) if level_str else PyramidLevel.MIDDLE
            s.add(
                RawMaterial(
                    name=row["name"],
                    category=row.get("category") or "",
                    cost_per_g=float(row.get("cost_per_g") or 0),
                    inventory_g=float(row.get("inventory_g") or 0),
                    fragrance_pyramid_level=level,
                )
            )
            added += 1
    return {"added": added, "skipped": skipped}
