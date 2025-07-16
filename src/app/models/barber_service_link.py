from sqlalchemy import ForeignKey, Table, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.app.database import Base
# from src.app.models.barber import Barber
from src.app.models.service import Service
# from src.app.models.barber import Barber

# barber_service = Table(
#     "barber_service",
#     Base.metadata,
# Column("duration", Integer),from src.app.models.barber import Barber
#     Column("barber_id", ForeignKey("barbers.id"), primary_key=True),
#     Column("service_id", ForeignKey("services.id"), primary_key=True),
# )


class BarberService(Base):
    __tablename__ = "barber_service"
    barber_id: Mapped[int] = mapped_column(ForeignKey("barbers.id"), primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), primary_key=True)
    duration: Mapped[int] = mapped_column(Integer, nullable=False) # Тривалість сервісу для цього барбера


    barber: Mapped["Barber"] = relationship(back_populates="barber_services")
    service: Mapped[Service] = relationship(back_populates="barber_services")
