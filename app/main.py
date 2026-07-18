"""FastAPI application for indoor, outdoor, and survey data."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import csv
from datetime import datetime, timezone
from io import StringIO
import logging
import sqlite3
from typing import Annotated, Any

from fastapi import FastAPI, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from app.config import Settings, load_settings
from app.database import Database
from app.schemas import (
    HealthResponse,
    IndoorReadingCreate,
    OutdoorReadingCreate,
    SavedResponse,
    SurveyAnswerCreate,
)

logger = logging.getLogger(__name__)
Limit = Annotated[int, Query(ge=1, le=1000)]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    database = Database(resolved_settings.database_path)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        database.initialize()
        yield

    application = FastAPI(
        title="University Environmental Sensing API",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.database = database
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(sqlite3.Error)
    async def database_error_handler(_: Request, error: sqlite3.Error) -> JSONResponse:
        logger.exception("Database operation failed", exc_info=error)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database operation failed"},
        )

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @application.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:
        return "You did it, you beautiful baby"

    @application.post(
        "/api/indoor",
        response_model=SavedResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_indoor(payload: IndoorReadingCreate) -> SavedResponse:
        received_at = utc_now()
        row_id = database.insert(
            """
            INSERT INTO indoor_readings (
                pod_id, recorded_at, received_at, temperature_c,
                relative_humidity_percent, mq135_adc_raw, mq135_voltage_mv,
                battery_voltage_v, sensor_warmup_seconds, wifi_rssi_dbm,
                response_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.pod_id,
                utc_iso(payload.recorded_at or received_at),
                utc_iso(received_at),
                payload.temperature_c,
                payload.relative_humidity_percent,
                payload.mq135_adc_raw,
                payload.mq135_voltage_mv,
                payload.battery_voltage_v,
                payload.sensor_warmup_seconds,
                payload.wifi_rssi_dbm,
                payload.response_code,
            ),
        )
        return SavedResponse(id=row_id)

    @application.post(
        "/api/outdoor",
        response_model=SavedResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_outdoor(payload: OutdoorReadingCreate) -> SavedResponse:
        received_at = utc_now()
        row_id = database.insert(
            """
            INSERT INTO outdoor_readings (
                location_id, recorded_at, received_at, temperature_c,
                incoming_radiation_w_m2, humidex,
                relative_humidity_percent, dew_point_c
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.location_id,
                utc_iso(payload.recorded_at or received_at),
                utc_iso(received_at),
                payload.temperature_c,
                payload.incoming_radiation_w_m2,
                payload.humidex,
                payload.relative_humidity_percent,
                payload.dew_point_c,
            ),
        )
        return SavedResponse(id=row_id)

    @application.post(
        "/api/survey-answer",
        response_model=SavedResponse,
    )
    def create_survey_answer(
        payload: SurveyAnswerCreate,
    ) -> JSONResponse:
        received_at = utc_now()
        row_id, created = database.save_survey_answer(
            {
                "survey_session_id": payload.survey_session_id,
                "location_id": payload.location_id,
                "pod_id": payload.pod_id,
                "question_id": payload.question_id,
                "response_value": payload.response_value,
                "answered_at": utc_iso(payload.answered_at or received_at),
                "received_at": utc_iso(received_at),
            }
        )
        response_status = (
            status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
        return JSONResponse(
            status_code=response_status,
            content=SavedResponse(id=row_id).model_dump(),
        )

    @application.get("/api/indoor")
    def get_indoor(
        limit: Limit = 100,
        pod_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        parameters: list[Any] = []
        add_filter(conditions, parameters, "pod_id", pod_id)
        add_time_filters(
            conditions, parameters, "recorded_at", start_time, end_time
        )
        return database.query(
            select_query("indoor_readings", conditions), (*parameters, limit)
        )

    @application.get("/api/outdoor")
    def get_outdoor(
        limit: Limit = 100,
        location_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        parameters: list[Any] = []
        add_filter(conditions, parameters, "location_id", location_id)
        add_time_filters(
            conditions, parameters, "recorded_at", start_time, end_time
        )
        return database.query(
            select_query("outdoor_readings", conditions), (*parameters, limit)
        )

    @application.get("/api/survey-answers")
    def get_survey_answers(
        limit: Limit = 100,
        survey_session_id: str | None = None,
        location_id: str | None = None,
        pod_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        parameters: list[Any] = []
        add_filter(
            conditions, parameters, "survey_session_id", survey_session_id
        )
        add_filter(conditions, parameters, "location_id", location_id)
        add_filter(conditions, parameters, "pod_id", pod_id)
        add_time_filters(
            conditions, parameters, "answered_at", start_time, end_time
        )
        return database.query(
            select_query("survey_answers", conditions), (*parameters, limit)
        )

    @application.get("/api/export/indoor.csv")
    def export_indoor() -> StreamingResponse:
        return csv_response(database, "indoor_readings", "indoor.csv")

    @application.get("/api/export/outdoor.csv")
    def export_outdoor() -> StreamingResponse:
        return csv_response(database, "outdoor_readings", "outdoor.csv")

    @application.get("/api/export/survey-answers.csv")
    def export_survey_answers() -> StreamingResponse:
        return csv_response(
            database, "survey_answers", "survey-answers.csv"
        )

    return application


def add_filter(
    conditions: list[str],
    parameters: list[Any],
    column: str,
    value: Any,
) -> None:
    if value is not None:
        conditions.append(f"{column} = ?")
        parameters.append(value)


def add_time_filters(
    conditions: list[str],
    parameters: list[Any],
    column: str,
    start_time: datetime | None,
    end_time: datetime | None,
) -> None:
    if start_time is not None:
        conditions.append(f"{column} >= ?")
        parameters.append(utc_iso(start_time))
    if end_time is not None:
        conditions.append(f"{column} <= ?")
        parameters.append(utc_iso(end_time))


def select_query(table: str, conditions: list[str]) -> str:
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    return f"SELECT * FROM {table}{where} ORDER BY received_at DESC, id DESC LIMIT ?"


def csv_response(database: Database, table: str, filename: str) -> StreamingResponse:
    columns, rows = database.fetch_table(table)
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(tuple(row[column] for column in columns) for row in rows)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


app = create_app()
