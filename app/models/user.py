import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum as SAEnum
from app.db.base import Base

class UserRole(str, enum.Enum):
    user = "user"
    manager = "manager"
    admin = "admin"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.user, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
