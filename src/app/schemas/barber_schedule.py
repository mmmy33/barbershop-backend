from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, Field, model_validator, ConfigDict
from pydantic_core import PydanticCustomError


class BarberScheduleBase(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="Day of the week")
    start_time: time = Field(..., description="Start time of work (HH:MM)")
    end_time: time = Field(..., description="End time of work (HH:MM)")

    @model_validator(mode="after")
    def validate_times(self) -> "BarberScheduleBase":
        if self.start_time >= self.end_time:
            raise PydanticCustomError(
                "time_validation",
                "Start time must be before end time",
            )
        return self
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "day_of_week": 1,
                    "start_time": "09:00",
                    "end_time": "18:00",
                }
            ]
        }
    }


class BarberScheduleCreate(BarberScheduleBase):
    """Schema for creating a new regular schedule entry."""
    pass


class BarberScheduleUpdate(BaseModel):
    """Schema for updating an existing regular schedule entry (all fields optional)."""
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    @model_validator(mode="after")
    def validate_update_times(self) -> "BarberScheduleUpdate":
        if self.start_time is not None and self.end_time is not None and self.start_time >= self.end_time:
            raise PydanticCustomError(
                "time_validation",
                "Start time must be before end time",
            )
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "start_time": "10:00",
                    "end_time": "19:00",
                }
            ]
        }
    }


class BarberScheduleInDB(BarberScheduleBase):
    """Schema for returning a regular schedule entry from the database."""
    id: int
    barber_id: int

    model_config = ConfigDict(from_attributes=True)


class BarberUnavailableTimeBase(BaseModel):
    """Base schema for creating/updating a barber's unavailable time."""
    start_time: datetime = Field(..., description="Start datetime of unavailability (ISO 8601)")
    end_time: datetime = Field(..., description="End datetime of unavailability (ISO 8601)")
    reason: Optional[str] = Field(None, max_length=255, description="Reason for unavailability (optional)")

    @model_validator(mode="after")
    def validate_datetimes(self) -> "BarberUnavailableTimeBase":
        if self.start_time >= self.end_time:
            raise PydanticCustomError(
                "datetime_validation",
                "Start datetime must be before end datetime.",
            )
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "start_datetime": "2025-06-15T10:00:00+03:00",
                    "end_datetime": "2025-06-15T12:00:00+03:00",
                    "reason": "Lunch break"
                }
            ]
        }
    }


class BarberUnavailableTimeCreate(BarberUnavailableTimeBase):
    """Schema for creating a new unavailable time entry."""
    pass


class BarberUnavailableTimeUpdate(BaseModel):
    """Schema for updating an existing unavailable time entry (all fields optional)."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    reason: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="after")
    def validate_update_times(self) -> "BarberUnavailableTimeUpdate":
        if self.start_time is not None and self.end_time is not None and self.start_time >= self.end_time:
            raise PydanticCustomError(
                "datetime_validation",
                "Start datetime must be before end datetime.",
            )
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "start_time": "2025-06-15T13:00:00Z",
                    "end_time": "2025-06-15T17:00:00Z",
                    "reason": "Meeting"
                }
            ]
        }
    }


class BarberUnavailableTimeInDB(BarberUnavailableTimeBase):
    """Schema for returning an unavailable time entry from the database."""
    id: int
    barber_id: int

    model_config = ConfigDict(from_attributes=True)
