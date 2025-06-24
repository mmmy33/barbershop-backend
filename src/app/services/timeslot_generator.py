from datetime import datetime, date, timedelta, timezone
from typing import List

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.addon import Addon
from src.app.models.appointment import Appointment
from src.app.models.barber_schedule import BarberSchedule
from src.app.models.barber_unavailable_time import BarberUnavailableTime
from src.app.models.service import Service




def calculate_total_duration(db: Session, service_id: int, addon_ids: list) -> timedelta:
    # Получаем основную услугу

    service = db.get(Service, service_id)
    if not service:
        raise ValueError("Service not found")

    # Длительность основной услуги
    service_duration = timedelta(minutes=service.duration)

    # Суммируем длительность всех добавочных услуг
    addons_duration = sum(
        (addon.duration for addon in db.scalars(
            select(Addon).where(Addon.id.in_(addon_ids))
        ).all())
    )
    return service_duration + timedelta(minutes=addons_duration)



def get_available_timeslots(
        db: Session,
        barber_id: int,
        target_date: date,
        service_id: int,
        slot_interval_minutes: int = 50,
        addon_ids: List[int] = None
) -> List[datetime]:
    if slot_interval_minutes <= 0:
        raise ValueError("slot_interval_minutes must be a positive integer and a divisor of 60.")

    day_of_week = target_date.weekday()
    schedule_entry = db.scalars(
        select(BarberSchedule)
        .where(BarberSchedule.barber_id == barber_id)
        .where(BarberSchedule.day_of_week == day_of_week)
    ).first()
    print(schedule_entry, "*" * 19,"barber_id", barber_id, "day_of_week", day_of_week)
    if not schedule_entry:
        return []

    working_start_time = schedule_entry.start_time
    working_end_time = schedule_entry.end_time

    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # service_duration_minutes = service.duration
    # service_duration = timedelta(minutes=service_duration_minutes)

    total_duration = calculate_total_duration(db=db, service_id=service_id, addon_ids=addon_ids)
    print("total_duration", total_duration)
    # print("duration", total_duration, "service_duration_minutes", service_duration_minutes)
    working_start_datetime_utc = datetime.combine(target_date, working_start_time).replace(tzinfo=timezone.utc)
    working_end_datetime_utc = datetime.combine(target_date, working_end_time).replace(tzinfo=timezone.utc)
    print("working_start_datetime_utc", working_start_datetime_utc)
    print("working_end_datetime_utc", working_end_datetime_utc)
    start_of_day_utc = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_of_day_utc = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)
    print("start_of_day_utc", start_of_day_utc)
    print("end_of_day_utc", end_of_day_utc)
    existing_appointments = db.scalars(
        select(Appointment)
        .where(Appointment.barber_id == barber_id)
        .where(Appointment.scheduled_time >= start_of_day_utc)
        .where(Appointment.scheduled_time < end_of_day_utc + timedelta(microseconds=1))
    ).all()

    print("existing_appointments", [appt.__dict__ for appt in existing_appointments])
    print("-" * 30)
    booked_intervals = []

    for appt in existing_appointments:
        start_utc = appt.scheduled_time.astimezone(timezone.utc)\
            if appt.scheduled_time.tzinfo else appt.scheduled_time.replace(tzinfo=timezone.utc)
        end_utc = start_utc + timedelta(minutes=appt.total_duration)
        print("+" * 30, end_utc, "+" * 30)
        booked_intervals.append({
            "start": start_utc,
            "end": end_utc
        })
        print(booked_intervals[0])
    unavailable_intervals_db = db.scalars(
        select(BarberUnavailableTime)
        .where(BarberUnavailableTime.barber_id == barber_id)
        .where(BarberUnavailableTime.start_time >= datetime.combine(
            target_date,
            datetime.min.time()))
        .where(
            BarberUnavailableTime.start_time < datetime.combine(target_date, datetime.min.time()) + timedelta(days=1))
    ).all()
    print("unavailable_intervals_db", [appts.__dict__ for appts in unavailable_intervals_db])
    print("*" * 30)
    for unavail_time in unavailable_intervals_db:
        start_utc = unavail_time.start_time.astimezone(
            timezone.utc) if unavail_time.start_time.tzinfo else unavail_time.start_time.replace(tzinfo=timezone.utc)
        end_utc = unavail_time.end_time.astimezone(
            timezone.utc) if unavail_time.end_time.tzinfo else unavail_time.end_time.replace(tzinfo=timezone.utc)

        booked_intervals.append({
            "start": start_utc,
            "end": end_utc
        })

    booked_intervals.sort(key=lambda x: x["start"])
    print("booked_intervals", booked_intervals)
    merged_booked_intervals = []
    if booked_intervals:
        current_merged = booked_intervals[0]
        for i in range(1, len(booked_intervals)):
            next_interval = booked_intervals[i]
            if next_interval["start"] <= current_merged["end"]:
                current_merged["end"] = max(current_merged["end"], next_interval["end"])
            else:
                merged_booked_intervals.append(current_merged)
                current_merged = next_interval
        merged_booked_intervals.append(current_merged)
    print("new_booked_intervals", merged_booked_intervals)
    available_slots = []
    current_slot_start = working_start_datetime_utc
    start_minute = current_slot_start.minute
    if start_minute % slot_interval_minutes != 0:
        current_slot_start += timedelta(minutes=(slot_interval_minutes - (start_minute % slot_interval_minutes)))
        current_slot_start = current_slot_start.replace(second=0, microsecond=0)

    while current_slot_start + total_duration <= working_end_datetime_utc:
        # print(current_slot_start)
        potential_slot_end = current_slot_start + total_duration
        is_available = True

        for booked in merged_booked_intervals:
            # print("=====", booked["start"], potential_slot_end, booked["end"])
            if not (potential_slot_end <= booked["start"] or current_slot_start >= booked["end"]):
                is_available = False
                current_slot_start = booked["end"] + timedelta(minutes=slot_interval_minutes)
                print("===" * 30, booked["start"], booked["end"])
                break

        if is_available:
            print("hello")
            available_slots.append(current_slot_start)
            # print(current_slot_start, "total_duration", total_duration, "potential_slot_end", potential_slot_end)
            current_slot_start +=  total_duration + timedelta(minutes=slot_interval_minutes)

    return available_slots



















# from sqlalchemy.ext.declarative import declarative_base
#
# from datetime import datetime, date, timedelta, timezone
# from typing import List
#
# from fastapi import HTTPException
# from sqlalchemy import select
# from sqlalchemy.orm import Session
#
# from src.app.models.appointment import Appointment
# from src.app.models.barber_schedule import BarberSchedule
# from src.app.models.barber_unavailable_time import BarberUnavailableTime
# from src.app.models.service import Service
#
# from sqlalchemy import Column, Integer, String
#
# Base = declarative_base()
#
# class Addon(Base):
#     __tablename__ = "addons"
#
#     id = Column(Integer, primary_key=True)
#     name = Column(String, index=True)
#     duration = Column(Integer)  # Продолжительность добавочной услуги (в минутах)
#     price = Column(Integer)  # Цена добавочной услуги
#
# def calculate_total_duration(db: Session, service_id: int, addon_ids: list) -> timedelta:
#     # Получаем основную услугу
#     service = db.get(Service, service_id)
#     if not service:
#         raise ValueError("Service not found")
#
#     # Длительность основной услуги
#     service_duration = timedelta(minutes=service.duration)
#
#     # Суммируем длительность всех добавочных услуг
#     addons_duration = sum(
#         (addon.duration for addon in db.scalars(
#             select(Addon).where(Addon.id.in_(addon_ids))
#         ).all())
#     )
#
#     return service_duration + timedelta(minutes=addons_duration)
#
# def get_available_timeslots(
#     db: Session,
#     barber_id: int,
#     target_date: date,
#     service_id: int,
#     addon_ids: list = [],  # Добавляем ids добавочных услуг
#     slot_interval_minutes: int = 50,
# ) -> List[datetime]:
#     # Рассчитываем общее время для услуги и добавочных
#     total_duration = calculate_total_duration(db, service_id, addon_ids)
#
#     # Получаем расписание для барбера
#     day_of_week = target_date.weekday()
#     schedule_entry = db.scalars(
#         select(BarberSchedule)
#         .where(BarberSchedule.barber_id == barber_id)
#         .where(BarberSchedule.day_of_week == day_of_week)
#     ).first()
#
#     if not schedule_entry:
#         return []
#
#     working_start_time = schedule_entry.start_time
#     working_end_time = schedule_entry.end_time
#
#     # Преобразуем в UTC
#     working_start_datetime_utc = datetime.combine(target_date, working_start_time).replace(tzinfo=timezone.utc)
#     working_end_datetime_utc = datetime.combine(target_date, working_end_time).replace(tzinfo=timezone.utc)
#
#     # Получаем список уже забронированных слотов
#     existing_appointments = db.scalars(
#         select(Appointment)
#         .where(Appointment.barber_id == barber_id)
#         .where(Appointment.scheduled_time >= working_start_datetime_utc)
#         .where(Appointment.scheduled_time < working_end_datetime_utc + timedelta(microseconds=1))
#     ).all()
#
#     booked_intervals = []
#
#     for appt in existing_appointments:
#         start_utc = appt.scheduled_time.astimezone(timezone.utc) if appt.scheduled_time.tzinfo else appt.scheduled_time.replace(tzinfo=timezone.utc)
#         end_utc = start_utc + timedelta(minutes=appt.total_duration)
#         booked_intervals.append({
#             "start": end_utc,
#             "end": end_utc
#         })
#
#     # Добавляем недоступное время для барбера
#     unavailable_intervals_db = db.scalars(
#         select(BarberUnavailableTime)
#         .where(BarberUnavailableTime.barber_id == barber_id)
#         .where(BarberUnavailableTime.start_time >= working_start_datetime_utc)
#         .where(BarberUnavailableTime.start_time < working_end_datetime_utc)
#     ).all()
#
#     for unavail_time in unavailable_intervals_db:
#         start_utc = unavail_time.start_time.astimezone(timezone.utc) if unavail_time.start_time.tzinfo else unavail_time.start_time.replace(tzinfo=timezone.utc)
#         end_utc = unavail_time.end_time.astimezone(timezone.utc) if unavail_time.end_time.tzinfo else unavail_time.end_time.replace(tzinfo=timezone.utc)
#         booked_intervals.append({
#             "start": start_utc,
#             "end": end_utc
#         })
#
#     # Сортируем и объединяем пересекающиеся интервалы
#     booked_intervals.sort(key=lambda x: x["start"])
#
#     merged_booked_intervals = []
#     if booked_intervals:
#         current_merged = booked_intervals[0]
#         for i in range(1, len(booked_intervals)):
#             next_interval = booked_intervals[i]
#             if next_interval["start"] <= current_merged["end"]:
#                 current_merged["end"] = max(current_merged["end"], next_interval["end"])
#             else:
#                 merged_booked_intervals.append(current_merged)
#                 current_merged = next_interval
#         merged_booked_intervals.append(current_merged)
#
#     # Генерация доступных слотов
#     available_slots = []
#     current_slot_start = working_start_datetime_utc
#     while current_slot_start + total_duration <= working_end_datetime_utc:
#         potential_slot_end = current_slot_start + total_duration
#         is_available = True
#
#         for booked in merged_booked_intervals:
#             if not (potential_slot_end <= booked["start"] or current_slot_start >= booked["end"]):
#                 is_available = False
#                 break
#
#         if is_available:
#             available_slots.append(current_slot_start)
#
#         # Сдвигаем слоты на интервал
#         current_slot_start += timedelta(minutes=slot_interval_minutes)
#
#     return available_slots
