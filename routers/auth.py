from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..deps import get_current_user, get_db
from ..models import User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut, user_out

router = APIRouter(prefix="/api/auth", tags=["Authentification"])


@router.post("/register", status_code=201, response_model=UserOut)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    return user_out(services.register_user(db, body.full_name, body.email, body.password))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    return TokenOut(access_token=services.authenticate(db, body.email, body.password))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user_out(user)
