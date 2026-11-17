from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.orm import Session

from .. import money, services
from ..deps import get_current_user, get_db
from ..models import User
from ..schemas import TransferIn

router = APIRouter(prefix="/api/transfers", tags=["Virements"])


@router.post("", status_code=201)
def create_transfer(
    body: TransferIn,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result, replayed = services.transfer(
        db, user, body.from_account_id, body.to_iban, money.to_millimes(body.amount),
        body.reference.strip() if body.reference else None, idempotency_key,
    )
    if replayed:
        response.headers["Idempotent-Replay"] = "true"
    return result
