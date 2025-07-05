from datetime import datetime, date, timedelta, timezone
from typing import List

from fastapi import HTTPException
from sqlalchemy import select, func
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

        # if not(merged_booked_intervals and available_slots ):
        #     check_interval = timedelta(0) if current_slot_start - timedelta(
        #         minutes=slot_interval_minutes) <= working_start_datetime_utc else timedelta(minutes=slot_interval_minutes)
        #     # check_interval = timedelta(0) if current_slot_start - timedelta(minutes=slot_interval_minutes) <= working_start_datetime_utc else timedelta(minutes=slot_interval_minutes)
        #     print("check_interval", check_interval)
        #     print("working_start_datetime_utc", working_start_datetime_utc )
        #     available_slots.append(current_slot_start - check_interval)
        #     current_slot_start +=  timedelta(minutes=slot_interval_minutes)
        #     continue

        for booked in merged_booked_intervals:
            # print("=====", booked["start"], potential_slot_end, booked["end"])
            if not (potential_slot_end <= booked["start"] or current_slot_start >= booked["end"]):
                is_available = False
                current_slot_start = booked["end"] + timedelta(minutes=slot_interval_minutes)
                available_slots.append(booked["end"])
                # print("===" * 30, booked["start"], booked["end"])
                break


        if is_available:

            # available_slots.append(potential_slot_end - timedelta(minutes=slot_interval_minutes))
            available_slots.append(current_slot_start)

            # available_slots.append(current_slot_start + timedelta(minutes=slot_interval_minutes))

            # print(current_slot_start, "total_duration", total_duration, "potential_slot_end", potential_slot_end)
            current_slot_start +=  timedelta(minutes=slot_interval_minutes)
    available_slots.sort()
    return available_slots



def check_availability(
    db: Session,
    barber_id: int,
    scheduled_time: datetime,  # must be UTC
    service_id: int,
    addon_ids: List[int] = None
):
    if addon_ids is None:
        addon_ids = []


    duration = calculate_total_duration(db, service_id, addon_ids)


    requested_start = (
        scheduled_time.astimezone(timezone.utc)
        if scheduled_time.tzinfo
        else scheduled_time.replace(tzinfo=timezone.utc)
    )
    requested_end = requested_start + duration


    day_of_week = scheduled_time.weekday()
    schedule_entry = db.scalars(
        select(BarberSchedule)
        .where(BarberSchedule.barber_id == barber_id)
        .where(BarberSchedule.day_of_week == day_of_week)
    ).first()

    if not schedule_entry:
        raise HTTPException(status_code=400, detail="The barber is not working on this day.")

    working_start_dt = datetime.combine(scheduled_time.date(), schedule_entry.start_time, tzinfo=timezone.utc)
    working_end_dt = datetime.combine(scheduled_time.date(), schedule_entry.end_time, tzinfo=timezone.utc)


    if not (working_start_dt <= requested_start and requested_end <= working_end_dt):
        raise HTTPException(status_code=400, detail="The requested time is outside the working hours.")


    existing_appointments = db.scalars(
        select(Appointment)
        .where(Appointment.barber_id == barber_id)
        .where(func.date(Appointment.scheduled_time) == scheduled_time.date())
    ).all()

    for appt in existing_appointments:
        appt_start = (
            appt.scheduled_time.astimezone(timezone.utc)
            if appt.scheduled_time.tzinfo
            else appt.scheduled_time.replace(tzinfo=timezone.utc)
        )
        appt_end = appt_start + timedelta(minutes=appt.total_duration)


        if not (requested_end <= appt_start or requested_start >= appt_end):
            raise HTTPException(status_code=400, detail="The time slot is already booked.")


    return True
