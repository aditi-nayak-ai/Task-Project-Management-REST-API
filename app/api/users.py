from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserResponse
from app.utils.dependencies import get_current_user, require_role
from app.utils.pagination import get_pagination
from app.core.audit import record_audit

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/", response_model=list[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
    pagination: tuple = Depends(get_pagination),
):
    offset, limit = pagination
    return db.query(User).order_by(User.id).offset(offset).limit(limit).all()


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_role(
    user_id: int,
    role: UserRole = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Privilege-escalation-adjacent action -- this is the one place a
    # regular account can become an admin, so it gets an explicit
    # before/after in the audit trail rather than relying on the
    # generic "something changed" shape used elsewhere.
    record_audit(
        db, current_user, "user.role.update", "user", user.id,
        detail={"from_role": user.role.value, "to_role": role.value},
    )
    user.role = role
    db.commit()
    db.refresh(user)
    return user
