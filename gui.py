# gui.py ── Formulair Pro Win · Fase 6 (historial & diff)

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, List

from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QTableView,
    QToolBar,
    QAction,
    QFileDialog,
    QMessageBox,
    QLabel,
    QInputDialog,
    QDialog,
    QTableWidget,
    QTableWidgetItem,
)
from qtawesome import icon

import services
import exporter
from dialogs import (
    LoginDialog,
    RawMaterialDialog,
    FormulaDialog,
    RevisionDiffDialog,
)
from auth import login
from session import current_user, require_role
from models import RawMaterial, Formula, Role


# ---------------------------------------------------------------------------#
# Table-models
# ---------------------------------------------------------------------------#
class _BaseModel(QAbstractTableModel):
    _headers: List[str] = []

    def __init__(self, items: List[Any]):
        super().__init__()
        self._items = items

    def rowCount(self, parent: QModelIndex = ...) -> int:  # type: ignore[override]
        return len(self._items)

    def columnCount(self, parent: QModelIndex = ...) -> int:  # type: ignore[override]
        return len(self._headers)

    def data(self, idx: QModelIndex, role: int = ...) -> Any:  # type: ignore[override]
        if not idx.isValid() or role != Qt.DisplayRole:
            return None
        obj = self._items[idx.row()]
        return getattr(obj, self._headers[idx.column()])

    def headerData(self, i, o, r):  # type: ignore[override]
        if o == Qt.Horizontal and r == Qt.DisplayRole:
            return self._headers[i].replace("_", " ").title()
        return super().headerData(i, o, r)


class RMModel(_BaseModel):
    _headers = ["id", "name", "category", "cost_per_g", "inventory_g"]


class FormulaModel(_BaseModel):
    _headers = ["id", "name", "description", "latest_rev"]  # latest_rev es col virtual

    def data(self, idx: QModelIndex, role: int = ...):
        if not idx.isValid() or role != Qt.DisplayRole:
            return None
        obj: Formula = self._items[idx.row()]
        col = self._headers[idx.column()]
        if col == "latest_rev":
            return obj.latest().number
        return super().data(idx, role)


# ---------------------------------------------------------------------------#
# TableTab genérico
# ---------------------------------------------------------------------------#
class TableTab(QWidget):
    def __init__(self, parent, model_cls, fetch_func):
        super().__init__(parent)
        self.model_cls = model_cls
        self.fetch = fetch_func

        self.table = QTableView()
        self.toolbar = QToolBar()
        self._setup_toolbar()

        lay = QVBoxLayout(self)
        lay.addWidget(self.toolbar)
        lay.addWidget(self.table)
        self.refresh()

    def _setup_toolbar(self):
        self.act_refresh = QAction(icon("mdi.reload"), "Actualizar", self, triggered=self.refresh)
        self.toolbar.addAction(self.act_refresh)

    def refresh(self):
        self.model = self.model_cls(self.fetch())
        self.table.setModel(self.model)
        self.table.resizeColumnsToContents()


# ---------------------------------------------------------------------------#
# Materias primas tab
# ---------------------------------------------------------------------------#
class RmTab(TableTab):
    def __init__(self, parent):
        super().__init__(parent, RMModel, lambda: services.list_all(RawMaterial))

    def _setup_toolbar(self):
        super()._setup_toolbar()
        act_add = QAction(icon("mdi.plus"), "Añadir", self, triggered=self._add_rm)
        act_add.setEnabled(require_role(Role.ADMIN, Role.PERFUMER))
        act_exp = QAction(icon("mdi.file-export"), "Exportar CSV", self, triggered=self._exp)
        act_imp = QAction(icon("mdi.file-import"), "Importar CSV", self, triggered=self._imp)
        self.toolbar.addActions([act_add, act_exp, act_imp])

    def _add_rm(self):
        dlg = RawMaterialDialog(self)
        data = dlg.get_data()
        if data:
            services.create_raw_material(**data)
            self.refresh()

    def _exp(self):
        f, _ = QFileDialog.getSaveFileName(self, "CSV", "", "CSV (*.csv)")
        if f:
            exporter.export_materials_csv(Path(f))

    def _imp(self):
        f, _ = QFileDialog.getOpenFileName(self, "CSV", "", "CSV (*.csv)")
        if f:
            services.import_materials_csv(Path(f))
            self.refresh()


# ---------------------------------------------------------------------------#
# Fórmulas tab con versiones
# ---------------------------------------------------------------------------#
class FormulaTab(TableTab):
    def __init__(self, parent):
        super().__init__(parent, FormulaModel, services.list_formulas)
        self.lbl_tot = QLabel()
        self.layout().addWidget(self.lbl_tot)
        self.refresh()

    # toolbar extra
    def _setup_toolbar(self):
        super()._setup_toolbar()
        self.act_new = QAction(icon("mdi.plus"), "Nueva", self, triggered=self._new_formula)
        self.act_clone = QAction(icon("mdi.content-copy"), "Clonar versión", self, triggered=self._clone)
        self.act_diff = QAction(icon("mdi.compare"), "Dif últimas", self, triggered=self._diff)
        self.act_hist = QAction(icon("mdi.history"), "Historial", self, triggered=self._hist)

        for a in (self.act_new, self.act_clone, self.act_diff, self.act_hist):
            self.toolbar.addAction(a)

    # helpers
    def _cur_formula(self) -> Formula | None:
        idx = self.table.currentIndex()
        return self.model._items[idx.row()] if idx.isValid() else None

    # acciones
    def _new_formula(self):
        dlg = FormulaDialog(self)
        data = dlg.get_data()
        if data:
            services.create_formula(data["name"], data["comment"], data["entries"])
            self.refresh()

    def _clone(self):
        f = self._cur_formula()
        if not f:
            return
        txt, ok = QInputDialog.getText(self, "Comentario", "Describe la nueva versión:")
        if ok:
            services.clone_revision(f.id, txt or "clonado GUI")
            self.refresh()

    def _diff(self):
        f = self._cur_formula()
        if not f or len(f.revisions) < 2:
            return
        RevisionDiffDialog(f.revisions[-2], f.revisions[-1], self).exec_()

    def _hist(self):
        f = self._cur_formula()
        if not f:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Historial • {f.name}")
        tbl = QTableWidget(len(f.revisions), 4)
        tbl.setHorizontalHeaderLabels(["Rev#", "Fecha", "Autor", "Comentario"])
        for r, rev in enumerate(f.revisions):
            tbl.setItem(r, 0, QTableWidgetItem(str(rev.number)))
            tbl.setItem(r, 1, QTableWidgetItem(str(rev.created_at.date())))
            tbl.setItem(r, 2, QTableWidgetItem(rev.author))
            tbl.setItem(r, 3, QTableWidgetItem(rev.comment))
        tbl.resizeColumnsToContents()
        lay = QVBoxLayout(dlg)
        lay.addWidget(tbl)
        dlg.exec_()

    # override refresh
    def refresh(self):
        super().refresh()
        forms = self.fetch()
        total = len(forms)
        revs = sum(len(f.revisions) for f in forms)
        self.lbl_tot.setText(f"<b>Fórmulas:</b> {total} &nbsp; <b>Revisiones totales:</b> {revs}")


# ---------------------------------------------------------------------------#
# MainWindow
# ---------------------------------------------------------------------------#
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Formulair Pro Win — Fase 6")
        self.resize(1100, 650)

        tabs = QTabWidget()
        tabs.addTab(RmTab(tabs), "Materias primas")
        tabs.addTab(FormulaTab(tabs), "Fórmulas")
        self.setCentralWidget(tabs)


# ---------------------------------------------------------------------------#
# bootstrap
# ---------------------------------------------------------------------------#
def main():
    import models

    models.init_db()

    app = QApplication(sys.argv)

    dlg = LoginDialog()
    u, p = dlg.get_credentials()
    if not login(u, p):
        QMessageBox.critical(None, "Login", "Credenciales incorrectas.")
        sys.exit(1)

    theme = Path("theme.qss")
    if theme.exists():
        app.setStyleSheet(theme.read_text(encoding="utf-8"))

    win = MainWindow()
    win.statusBar().showMessage(
        f"Conectado como {current_user().username} ({current_user().role})"
    )
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
