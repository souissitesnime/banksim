from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import services
from ..deps import get_db, require_admin
from ..models import User
from ..schemas import AccountOut, UserOut, account_out, user_out

router = APIRouter(prefix="/api/admin", tags=["Administration"])


@router.post("/accounts/{account_id}/freeze", response_model=AccountOut)
def freeze(account_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return account_out(services.set_frozen(db, admin, account_id, True))


@router.post("/accounts/{account_id}/unfreeze", response_model=AccountOut)
def unfreeze(account_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return account_out(services.set_frozen(db, admin, account_id, False))


@router.post("/users/{user_id}/unlock", response_model=UserOut)
def unlock(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return user_out(services.unlock_user(db, admin, user_id))


@router.get("/audit-log")
def audit_log(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
              admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    items, total = services.list_audit(db, limit, offset)
    return {
        "items": [
            {"id": a.id, "ts": a.ts.isoformat(), "actor_id": a.actor_id, "action": a.action,
             "entity": a.entity, "entity_id": a.entity_id, "details": a.details}
            for a in items
        ],
        "total": total, "limit": limit, "offset": offset,
    }
