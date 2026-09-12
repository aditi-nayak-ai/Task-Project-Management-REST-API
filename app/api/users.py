from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserResponse
from app.utils.dependencies import get_current_user, require_role
from app.utils.pagination import get_pagination

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
    _: User = Depends(require_role("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    db.commit()
    db.refresh(user)
    return user
