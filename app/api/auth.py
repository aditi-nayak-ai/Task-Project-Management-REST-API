from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.user import UserCreate, UserResponse, Token, RefreshRequest, AccessTokenResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from app.core.limiter import limiter
from app.core.logging_config import logger
from datetime import datetime, timezone

router = APIRouter()


def _issue_token_pair(user: User, db: Session) -> Token:
    access_token = create_access_token(data={"sub": user.email, "role": user.role.value})
    raw_refresh, token_hash, expires_at = generate_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    db.commit()
    return Token(access_token=access_token, refresh_token=raw_refresh, token_type="bearer")


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("10/minute")
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(email=user.email, hashed_password=hash_password(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info("New user registered: %s", new_user.email)
    return new_user


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    return _issue_token_pair(user, db)


@router.post("/refresh", response_model=AccessTokenResponse)
@limiter.limit("30/minute")
def refresh_access_token(request: Request, payload: RefreshRequest, db: Session = Depends(get_db)):
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    if not stored or stored.revoked:
        raise invalid
    if stored.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise invalid

    user = db.query(User).filter(User.id == stored.user_id).first()
    if not user or not user.is_active:
        raise invalid

    access_token = create_access_token(data={"sub": user.email, "role": user.role.value})
    return AccessTokenResponse(access_token=access_token, token_type="bearer")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    """
    Revokes the refresh token. This does NOT invalidate any access token
    already issued — those remain valid for the rest of their (short)
    lifetime, an inherent tradeoff of stateless JWTs. Shrinking that
    window further (shorter access TTL, or an access-token blocklist)
    is a call for whoever owns the security posture of this API, not
    something to bake in silently.
    """
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if stored:
        stored.revoked = True
        db.commit()
    return None
