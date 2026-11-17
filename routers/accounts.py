from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import money, services
from ..deps import get_current_user, get_db
from ..models import User
from ..schemas import (AccountCreateIn, AccountOut, AmountIn, ProjectionOut, TransactionOut, TransactionPage,
                       TransactionType, account_out, transaction_out)

router = APIRouter(prefix="/api/accounts", tags=["Comptes"])


@router.post("", status_code=201, response_model=AccountOut)
def open_account(body: AccountCreateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return account_out(services.create_account(db, user, body.type))


@router.get("", response_model=list[AccountOut])
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [account_out(a) for a in services.list_accounts(db, user)]


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return account_out(services.get_account(db, user, account_id))


@router.post("/{account_id}/close", response_model=AccountOut)
def close_account(account_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return account_out(services.close_account(db, user, account_id))


@router.post("/{account_id}/deposit", status_code=201, response_model=TransactionOut)
def deposit(account_id: int, body: AmountIn, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    return transaction_out(services.deposit(db, user, account_id, money.to_millimes(body.amount)))


@router.post("/{account_id}/withdraw", status_code=201, response_model=TransactionOut)
def withdraw(account_id: int, body: AmountIn, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    return transaction_out(services.withdraw(db, user, account_id, money.to_millimes(body.amount)))


@router.get("/{account_id}/transactions", response_model=TransactionPage)
def transactions(account_id: int, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                 type: TransactionType | None = None, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    items, total = services.list_transactions(db, user, account_id, limit, offset, type)
    return TransactionPage(items=[transaction_out(t) for t in items], total=total, limit=limit, offset=offset)


@router.get("/{account_id}/interest-projection", response_model=ProjectionOut)
def interest_projection(account_id: int, days: int = Query(30, ge=1, le=365),
                        user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.interest_projection(db, user, account_id, days)
