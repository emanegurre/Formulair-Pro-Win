# auth.py ── autenticación simple

from passlib.hash import pbkdf2_sha256
from models import SessionLocal, User, Role

_current_user: User | None = None


def login(username: str, password: str) -> bool:
    global _current_user
    with SessionLocal() as s:
        user = s.query(User).filter_by(username=username, is_active=True).first()
        if user and pbkdf2_sha256.verify(password, user.password_hash):
            _current_user = user
            return True
    return False


def current_user() -> User | None:
    return _current_user


def require_role(*roles: Role) -> bool:
    u = current_user()
    return bool(u and u.role in roles)
