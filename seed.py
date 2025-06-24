from sqlalchemy.orm import Session

from src.app.database import SessionLocal
from src.app.models.addon import Addon
from src.app.models.barber import Barber
from src.app.models.service import Service
from src.app.models.appointment import Appointment


# def run_seed_script():
#     db: Session = SessionLocal()
#
#     db.commit()
#
#     # Barbers create
#     barber1 = Barber(name="John")
#     barber2 = Barber(name="Jack")
#
#     # Services
#     service1 = Service(name="Haircut", price=100, duration=60)
#     service2 = Service(name="Beard Trim", price=50, duration=30)
#
#     # Addons
#     addon1 = Addon(name="Beard care", price=50, duration=30)
#     addon2 = Addon(name="Hair care", price=30, duration=30)
#
#     barber1.services = [service1, service2]
#     barber2.services = [service1, service2]
#
#     barber1.addons = [addon1, addon2]
#     barber2.addons = [addon1, addon2]
#
#     db.add_all([barber1, barber2, service1, service2, addon1, addon2])
#     db.commit()
#     db.close()
#
#     print("✅ Seed completed")



def run_seed_script():
    db: Session = SessionLocal()

    db.commit()

    # Barbers create
    barber1 = Barber(name="John")
    barber2 = Barber(name="Jack")

    # Services
    service1 = Service(name="Haircut", price=100, duration=60)
    service2 = Service(name="Beard Trim", price=50, duration=30)

    # Addons
    addon1 = Addon(name="Beard care", price=50, duration=30)
    addon2 = Addon(name="Hair care", price=30, duration=30)

    barber1.services = [service1, service2]
    barber2.services = [service1, service2]

    barber1.addons = [addon1, addon2]
    barber2.addons = [addon1, addon2]

    # Schedules
    from datetime import time
    from src.app.models.barber_schedule import BarberSchedule

    schedule1 = BarberSchedule(barber=barber1, day_of_week=0, start_time=time(9, 0), end_time=time(17, 0))
    schedule2 = BarberSchedule(barber=barber2, day_of_week=1, start_time=time(10, 0), end_time=time(18, 0))

    db.add_all([barber1, barber2, service1, service2, addon1, addon2, schedule1, schedule2])
    db.commit()
    db.close()

    print("✅ Seed completed")



if __name__ == "__main__":
    run_seed_script()
