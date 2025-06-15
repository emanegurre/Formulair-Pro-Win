# auth.py ── autenticación simple

from passlib.hash import pbkdf2_sha256
from models import SessionLocal, User
from session import set_current_user


def login(username: str, password: str) -> bool:
    with SessionLocal() as s:
        user = s.query(User).filter_by(username=username, is_active=True).first()
        if user and pbkdf2_sha256.verify(password, user.password_hash):
            set_current_user(user)
            return True
    return False

