"""Pydantic request and response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _non_empty(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be empty")
    return value


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class IndoorReadingCreate(StrictRequest):
    pod_id: str
    recorded_at: datetime | None = None
    temperature_c: float
    relative_humidity_percent: float = Field(ge=0, le=100)
    mq135_adc_raw: int = Field(ge=0, le=4095)
    mq135_voltage_mv: int = Field(ge=0)
    battery_voltage_v: float | None = Field(default=None, ge=0)
    sensor_warmup_seconds: int | None = Field(default=None, ge=0)
    wifi_rssi_dbm: int | None = None
    response_code: Literal[1, 2, 3] | None = None

    _validate_pod_id = field_validator("pod_id")(_non_empty)


class OutdoorReadingCreate(StrictRequest):
    location_id: str
    recorded_at: datetime | None = None
    temperature_c: float
    incoming_radiation_w_m2: float | None = Field(default=None, ge=0)
    humidex: float | None = None
    relative_humidity_percent: float = Field(ge=0, le=100)
    dew_point_c: float | None = None

    _validate_location_id = field_validator("location_id")(_non_empty)


class SurveyAnswerCreate(StrictRequest):
    survey_session_id: str
    location_id: str
    pod_id: str | None = None
    question_id: str
    response_value: int = Field(ge=1, le=5)
    answered_at: datetime | None = None

    _validate_required_strings = field_validator(
        "survey_session_id", "location_id", "question_id"
    )(_non_empty)

    @field_validator("pod_id")
    @classmethod
    def validate_optional_pod_id(cls, value: str | None) -> str | None:
        return _non_empty(value) if value is not None else None


class SavedResponse(BaseModel):
    status: Literal["saved"] = "saved"
    id: int


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
