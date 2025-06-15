# dialogs.py ── Login · Materia prima · Fórmula · Diff revisiones

from __future__ import annotations
from typing import List, Tuple

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QDoubleSpinBox,
    QComboBox,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QSpinBox,
    QPushButton,
    QVBoxLayout,
    QMessageBox,
)
from PyQt5.QtCore import Qt

import services
from models import PyramidLevel, RawMaterial


# ---------------------------------------------------------------------------#
# Login
# ---------------------------------------------------------------------------#
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Iniciar sesión")
        self.txt_user = QLineEdit()
        self.txt_pass = QLineEdit(echoMode=QLineEdit.Password)
        lay = QFormLayout(self)
        lay.addRow("Usuario", self.txt_user)
        lay.addRow("Contraseña", self.txt_pass)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_credentials(self):
        if self.exec_() == QDialog.Accepted:
            return self.txt_user.text(), self.txt_pass.text()
        return None, None


# ---------------------------------------------------------------------------#
# Materia prima
# ---------------------------------------------------------------------------#
class RawMaterialDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva materia prima")
        self.setModal(True)

        self.txt_name = QLineEdit()
        self.dsb_cost = QDoubleSpinBox(decimals=4, maximum=9999, suffix=" €/g")
        self.dsb_ifra = QDoubleSpinBox(decimals=2, maximum=100, suffix=" %")
        self.cbo_level = QComboBox()
        self.cbo_level.addItems([lvl.value for lvl in PyramidLevel])
        self.txt_notes = QTextEdit()

        lay = QFormLayout(self)
        lay.addRow("Nombre*", self.txt_name)
        lay.addRow("Coste", self.dsb_cost)
        lay.addRow("Límite IFRA", self.dsb_ifra)
        lay.addRow("Nivel pirámide", self.cbo_level)
        lay.addRow("Notas", self.txt_notes)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_data(self):
        if self.exec_() == QDialog.Accepted:
            if not self.txt_name.text().strip():
                QMessageBox.warning(self, "Error", "Nombre obligatorio.")
                return None
            return dict(
                name=self.txt_name.text().strip(),
                cost_per_g=self.dsb_cost.value(),
                ifra_limit_pct=self.dsb_ifra.value(),
                fragrance_pyramid_level=self.cbo_level.currentText(),
                notes=self.txt_notes.toPlainText(),
            )
        return None


# ---------------------------------------------------------------------------#
# Fórmula (creación/clonado rápido)
# ---------------------------------------------------------------------------#
class FormulaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva fórmula")
        self.txt_name = QLineEdit()
        self.txt_comment = QTextEdit()

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Materia prima", "Peso g", "Dil ID"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self._materials: List[RawMaterial] = services.list_all(RawMaterial)
        self._add_row()

        btn_add_row = QPushButton("+ fila")
        btn_add_row.clicked.connect(self._add_row)

        lay = QVBoxLayout(self)
        f = QFormLayout()
        f.addRow("Nombre*", self.txt_name)
        f.addRow("Comentario", self.txt_comment)
        lay.addLayout(f)
        lay.addWidget(self.tbl)
        lay.addWidget(btn_add_row)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _add_row(self):
        r = self.tbl.rowCount()
        self.tbl.insertRow(r)
        self.tbl.setItem(r, 0, QTableWidgetItem())
        spin = QSpinBox()
        spin.setRange(0, 1000)
        self.tbl.setCellWidget(r, 1, spin)
        self.tbl.setItem(r, 2, QTableWidgetItem())

    def _collect(self) -> List[Tuple[int, float, str | None]]:
        out = []
        for r in range(self.tbl.rowCount()):
            name = self.tbl.item(r, 0).text().strip()
            w = self.tbl.cellWidget(r, 1).value()
            dil = self.tbl.item(r, 2).text().strip()
            if not name or w == 0:
                continue
            rm = next((m for m in self._materials if m.name == name), None)
            if not rm:
                raise ValueError(f"Materia {name!r} no encontrada.")
            out.append((rm.id, w, dil or None))
        return out

    def get_data(self):
        if self.exec_() == QDialog.Accepted:
            if not self.txt_name.text().strip():
                QMessageBox.warning(self, "Error", "Nombre obligatorio.")
                return None
            try:
                entries = self._collect()
            except ValueError as e:
                QMessageBox.warning(self, "Error", str(e))
                return None
            if not entries:
                QMessageBox.warning(self, "Error", "Añade al menos una fila válida.")
                return None
            return {
                "name": self.txt_name.text().strip(),
                "comment": self.txt_comment.toPlainText().strip(),
                "entries": entries,
            }
        return None


# ---------------------------------------------------------------------------#
# Diff revisiones
# ---------------------------------------------------------------------------#
class RevisionDiffDialog(QDialog):
    def __init__(self, rev_a, rev_b, parent=None):
        super().__init__(parent)
        from PyQt5.QtWidgets import QTextEdit
        self.setWindowTitle(f"Diferencias v{rev_a.number} ↔ v{rev_b.number}")
        txt = QTextEdit(readOnly=True)
        txt.setPlainText(services.diff_revisions(rev_a.id, rev_b.id))
        lay = QVBoxLayout(self)
        lay.addWidget(txt)
        btn = QDialogButtonBox(QDialogButtonBox.Close)
        btn.rejected.connect(self.reject)
        lay.addWidget(btn)
