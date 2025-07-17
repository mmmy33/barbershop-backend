from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime
from src.app.database import Base

from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(default="user")
    barber: Mapped[Optional["Barber"]] = relationship("Barber", back_populates="user", uselist=False)

    is_verified: Mapped[bool] = mapped_column(default=False)
    verification_code: Mapped[str] = mapped_column(String(6), nullable=True)
    verification_code_expires: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="user")
