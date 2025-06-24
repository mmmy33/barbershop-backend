from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, Table, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.types import DateTime

from src.app.database import Base
from src.app.models.appointment_addon_link import appointment_addon

from src.app.models.user import User


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column()
    phone_number: Mapped[str] = mapped_column()
    barber_id: Mapped[int] = mapped_column(ForeignKey("barbers.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    total_duration: Mapped[int] = mapped_column()
    total_price: Mapped[int] = mapped_column()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user = relationship("User", back_populates="appointments")
    barber = relationship("Barber", backref="appointments_from_barber")
    service = relationship("Service", backref="appointments_from_service")
    addons = relationship("Addon", secondary=appointment_addon, back_populates="appointments")
