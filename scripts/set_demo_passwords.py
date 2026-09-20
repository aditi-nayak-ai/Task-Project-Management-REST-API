"""
Create or reset the three demo accounts used by the dashboard's "Try as ..." buttons.
 
Idempotent: re-running it resets each account's password and role. Passwords come
from environment variables, never from the repo:
 
    DATABASE_URL=<postgres url> SECRET_KEY=<any 32+ char string> \\
    DEMO_ADMIN_PASSWORD=... DEMO_MANAGER_PASSWORD=... DEMO_VIEWER_PASSWORD=... \\
    python -m scripts.set_demo_passwords
 
Use the same three passwords as the DEMO_*_PASSWORD secrets in the dashboard's
Streamlit settings.
"""
import os
import sys
 
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole
 
ACCOUNTS = [
    ("admin@taskdemo.com", "DEMO_ADMIN_PASSWORD", UserRole.admin),
    ("manager@taskdemo.com", "DEMO_MANAGER_PASSWORD", UserRole.manager),
    ("viewer@taskdemo.com", "DEMO_VIEWER_PASSWORD", UserRole.user),
]
 
 
def main() -> None:
    missing = [env for _, env, _ in ACCOUNTS if not os.environ.get(env)]
    if missing:
        sys.exit(f"Set these environment variables first: {', '.join(missing)}")
 
    for _, env, _ in ACCOUNTS:
        if not 8 <= len(os.environ[env]) <= 72:
            sys.exit(f"{env} must be between 8 and 72 characters.")
 
    db = SessionLocal()
    try:
        for email, env, role in ACCOUNTS:
            user = db.query(User).filter(User.email == email).first()
            if user:
                user.hashed_password = hash_password(os.environ[env])
                user.role = role
                user.is_active = True
                action = "updated"
            else:
                db.add(User(
                    email=email,
                    hashed_password=hash_password(os.environ[env]),
                    role=role,
                    is_active=True,
                ))
                action = "created"
            print(f"{action}: {email} ({role.value})")
        db.commit()
    finally:
        db.close()
 
 
if __name__ == "__main__":
    main()
