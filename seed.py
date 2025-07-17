from sqlalchemy.orm import Session

from src.app.auth.security import hash_password
from src.app.database import SessionLocal
from src.app.models.addon import Addon
from src.app.models.barber import Barber
from src.app.models.barber_service_link import BarberService
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

    # === Users (для зв'язку з Barber)
    from src.app.models.user import User
    user1 = User(name="Ivan", email="ivanko@example.com", hashed_password=hash_password("hashed_pw1"), role="barber")
    user2 = User(name="Maria", email="maria@example.com", hashed_password=hash_password("hashed_pw2"), role="barber")

    db.add_all([user1, user2])
    db.flush()

    # === Barbers (пов'язані з користувачами)
    barber1 = Barber(name="Іванко Барбер", user_id=user1.id)
    barber2 = Barber(name="Марія Стиліст", user_id=user2.id)

    # === Services
    service1 = Service(name="Чоловіча стрижка", price=250)
    service2 = Service(name="Гоління", price=150)
    service3 = Service(name="Дитяча стрижка", price=200)
    service4 = Service(name="Жіноча укладка", price=400)

    # === Addons
    addon1 = Addon(name="Догляд за бородою", price=50, duration=30)
    addon2 = Addon(name="Догляд за волоссям", price=30, duration=30)

    db.add_all([barber1, barber2, service1, service2, service3, service4, addon1, addon2])
    db.flush()

    # === Barber Services
    barber_service1 = BarberService(barber=barber1, service=service1, duration=30)
    barber_service2 = BarberService(barber=barber1, service=service2, duration=20)
    barber_service3 = BarberService(barber=barber2, service=service1, duration=40)
    barber_service4 = BarberService(barber=barber2, service=service3, duration=25)
    barber_service5 = BarberService(barber=barber2, service=service4, duration=60)

    # === Assign Addons
    barber1.addons.extend([addon1, addon2])
    barber2.addons.append(addon1)

    # === Schedules
    from datetime import time
    from src.app.models.barber_schedule import BarberSchedule

    schedule1 = BarberSchedule(barber=barber1, day_of_week=0, start_time=time(9, 0), end_time=time(17, 0))
    schedule2 = BarberSchedule(barber=barber2, day_of_week=1, start_time=time(10, 0), end_time=time(18, 0))
    schedule3 = BarberSchedule(barber=barber1, day_of_week=2, start_time=time(9, 30), end_time=time(17, 30))

    db.add_all([
        barber_service1, barber_service2, barber_service3,
        barber_service4, barber_service5,
        schedule1, schedule2, schedule3
    ])

    db.commit()
    db.close()
    print("✅ Seed completed")


if __name__ == "__main__":
    run_seed_script()

