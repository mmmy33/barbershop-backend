from sqlalchemy.orm import Mapped, mapped_column, relationship
# from src.app.models.barber_service_link import barber_service
from src.app.database import Base
# from src.app.models.barber_service_link import BarberService

class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column()
    price: Mapped[int] = mapped_column()

    # barbers = relationship("Barber", secondary=barber_service, back_populates="services")
    barber_services: Mapped[list["BarberService"]] = relationship(back_populates="service")