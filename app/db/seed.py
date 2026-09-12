import os
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.core.security import hash_password
from app.core.logging_config import logger


def seed_first_admin(db: Session) -> None:
    """
    Every admin-only action in this API (create_project, update_role,
    etc.) requires an existing admin to already be logged in. The
    original project had no path to create that first admin at all --
    the README's demo credentials imply someone manually inserted rows
    into the deployed database out-of-band, which isn't reproducible by
    anyone else standing this project up.

    This runs once at startup, only creates an admin if ZERO admins
    exist yet (idempotent -- safe to leave on across restarts), and does
    nothing if ADMIN_EMAIL/ADMIN_PASSWORD aren't set so it's opt-in per
    environment rather than a surprise account showing up everywhere.
    """
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        return

    admin_exists = db.query(User).filter(User.role == UserRole.admin).first()
    if admin_exists:
        return

    existing_user = db.query(User).filter(User.email == admin_email).first()
    if existing_user:
        existing_user.role = UserRole.admin
        db.commit()
        logger.info("Promoted existing user %s to admin.", admin_email)
        return

    admin = User(
        email=admin_email,
        hashed_password=hash_password(admin_password),
        role=UserRole.admin,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    logger.info("Seeded first admin account: %s", admin_email)
