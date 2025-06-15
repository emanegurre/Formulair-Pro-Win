# models.py ── Formulair Pro Win · Fase 6   (versión sin error de sintaxis)
# ==================================================================================

from __future__ import annotations
import enum
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
    validates,
)
from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------#
# Base
# ---------------------------------------------------------------------------#


class Base(DeclarativeBase):
    def __repr__(self) -> str:
        cols = ", ".join(
            f"{c.key}={getattr(self, c.key)!r}" for c in list(self.__table__.columns)[:3]
        )
        return f"<{self.__class__.__name__} {cols} …>"


# ---------------------------------------------------------------------------#
# Usuarios, roles y auditoría
# ---------------------------------------------------------------------------#


class Role(str, enum.Enum):
    ADMIN = "admin"
    PERFUMER = "perfumista"
    GUEST = "invitado"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.GUEST)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="logs")


# ---------------------------------------------------------------------------#
# Materias y stock
# ---------------------------------------------------------------------------#


class PyramidLevel(str, enum.Enum):
    TOP = "top"
    MIDDLE = "middle"
    BASE = "base"


class RawMaterial(Base):
    __tablename__ = "raw_materials"
    __table_args__ = (
        UniqueConstraint("name", name="uq_rm_name"),
        CheckConstraint("inventory_g >= 0", name="ck_inv_nonneg"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(64))
    cost_per_g: Mapped[float] = mapped_column(Float, default=0.0)
    inventory_g: Mapped[float] = mapped_column(Float, default=0.0)
    low_stock_threshold_g: Mapped[float] = mapped_column(Float, default=100)
    fragrance_pyramid_level: Mapped[PyramidLevel] = mapped_column(
        Enum(PyramidLevel), default=PyramidLevel.MIDDLE
    )

    movements: Mapped[List["InventoryMovement"]] = relationship(
        back_populates="raw_material", cascade="all, delete-orphan"
    )


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (CheckConstraint("delta_g != 0", name="ck_delta_nonzero"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_material_id: Mapped[int] = mapped_column(ForeignKey("raw_materials.id"))
    delta_g: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    raw_material: Mapped["RawMaterial"] = relationship(back_populates="movements")


# ---------------------------------------------------------------------------#
# Versionado de fórmulas
# ---------------------------------------------------------------------------#


class Formula(Base):
    __tablename__ = "formulas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    revisions: Mapped[List["FormulaRevision"]] = relationship(
        back_populates="formula",
        order_by="FormulaRevision.number",
        cascade="all, delete-orphan",
    )

    def latest(self) -> "FormulaRevision":
        return self.revisions[-1]


class FormulaRevision(Base):
    __tablename__ = "formula_revisions"
    __table_args__ = (UniqueConstraint("formula_id", "number", name="uq_form_rev"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    formula_id: Mapped[int] = mapped_column(ForeignKey("formulas.id"))
    number: Mapped[int] = mapped_column(Integer)  # 1,2,3…
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    author: Mapped[str] = mapped_column(String(40))
    comment: Mapped[Optional[str]] = mapped_column(Text)

    formula: Mapped["Formula"] = relationship(back_populates="revisions")
    entries: Mapped[List["FormulaEntry"]] = relationship(
        back_populates="revision", cascade="all, delete-orphan"
    )

    def total_weight(self) -> float:
        return float(sum(e.weight_g for e in self.entries))

    def cost_estimate(self) -> float:
        return float(sum(e.weight_g * e.raw_material.cost_per_g for e in self.entries))


class FormulaEntry(Base):
    __tablename__ = "formula_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey("formula_revisions.id"))
    raw_material_id: Mapped[int] = mapped_column(ForeignKey("raw_materials.id"))
    weight_g: Mapped[float] = mapped_column(Float, nullable=False)
    dilution: Mapped[Optional[str]] = mapped_column(String(40))

    revision: Mapped["FormulaRevision"] = relationship(back_populates="entries")
    raw_material: Mapped["RawMaterial"] = relationship()

    @validates("weight_g")
    def _validate_weight(self, _, v):
        if v <= 0:
            raise ValueError("Peso debe ser > 0")
        return v


# ---------------------------------------------------------------------------#
# Engine y semilla
# ---------------------------------------------------------------------------#
_DB_PATH = Path(__file__).with_name("formulair.db")
engine = create_engine(f"sqlite:///{_DB_PATH}", future=True)
SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)


def get_engine() -> Engine:
    """Return the application's SQLAlchemy engine."""
    return engine


def init_db(drop: bool = False):
    from passlib.hash import pbkdf2_sha256
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    if drop:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with Session(engine) as s:
        if not s.scalar(select(User).where(User.username == "admin")):
            s.add(
                User(
                    username="admin",
                    password_hash=pbkdf2_sha256.hash("admin"),
                    role=Role.ADMIN,
                )
            )
        if not s.scalar(select(RawMaterial).where(RawMaterial.name == "Bergamot EO")):
            s.add(RawMaterial(name="Bergamot EO", cost_per_g=0.1, inventory_g=500))
        if not s.scalar(select(Formula).where(Formula.name == "Demo EDP")):
            berg = s.scalar(select(RawMaterial).where(RawMaterial.name == "Bergamot EO"))
            form = Formula(name="Demo EDP")
            rev = FormulaRevision(number=1, author="seed", comment="versión inicial")
            rev.entries.append(FormulaEntry(raw_material=berg, weight_g=30))
            form.revisions.append(rev)
            s.add(form)
        s.commit()


if __name__ == "__main__":
    init_db()

