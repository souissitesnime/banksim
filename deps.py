"""Dépendances FastAPI : session de base, utilisateur courant, rôle administrateur."""
from __future__ import annotations

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import security
from .errors import BankError
from .models import User

_bearer = HTTPBearer(auto_error=False)


def get_db(request: Request):
    db = request.app.state.SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise BankError(401, "UNAUTHENTICATED", "Authentification requise.")
    try:
        payload = security.decode_token(creds.credentials)
    except jwt.ExpiredSignatureError:
        raise BankError(401, "TOKEN_EXPIRED", "Session expirée, reconnectez-vous.") from None
    except jwt.PyJWTError:
        raise BankError(401, "INVALID_TOKEN", "Jeton invalide.") from None
    try:
        user = db.get(User, int(payload["sub"]))
    except (ValueError, TypeError):
        user = None
    if user is None:
        raise BankError(401, "INVALID_TOKEN", "Jeton invalide.")
    if user.status == "LOCKED":
        raise BankError(423, "ACCOUNT_LOCKED", "Compte utilisateur verrouillé.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "ADMIN":
        raise BankError(403, "FORBIDDEN", "Droits administrateur requis.")
    return user
