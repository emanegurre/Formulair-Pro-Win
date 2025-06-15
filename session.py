from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import QApplication

from models import User, Role


def set_current_user(user: Optional[User]) -> None:
    app = QApplication.instance()
    if app:
        app.setProperty("current_user", user)


def current_user() -> Optional[User]:
    app = QApplication.instance()
    if app:
        return app.property("current_user")
    return None


def require_role(*roles: Role) -> bool:
    u = current_user()
    return bool(u and u.role in roles)
