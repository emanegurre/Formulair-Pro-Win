# Formulair Pro Win  
Software de formulación y control de stock para perfumistas artesanales
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-%23777bb5)

---

## ✨ Características clave

| Módulo | Descripción |
|--------|-------------|
| **Materias primas** | Inventario con coste €/g, umbral de stock bajo y movimientos históricos. |
| **Fórmulas con versiones (Fase 6)** | Cada cambio crea una *revisión* (v1, v2…) con diff visual y clonación. |
| **Pirámide olfativa PDF** | Exporta pirámide Top/Middle/Base con colores e ingredientes. |
| **Import / Export CSV** | Materias y fórmulas; evita duplicados y valida datos. |
| **Usuarios & roles** | _admin_, _perfumista_, _invitado_ con login y bloqueo de acciones. |
| **Auditoría** | Log “quién-cuándo-qué” para altas, clones y ajustes de stock. |
| **Sincronización SQLite → PostgreSQL** | Script `sync.py` para backup o trabajo multi-equipo. |
| **Empaquetado** | Compatible con PyInstaller / MSIX para distribución en Windows 11. |

---

## 📦 Instalación rápida (dev)

```bash
git clone https://github.com/tuUsuario/Formulair-Pro-Win.git
cd Formulair-Pro-Win
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
python gui.py        # login: admin / admin

