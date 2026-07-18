from collections.abc import Iterator

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    app = create_app(Settings(database_path=tmp_path / "test.db"))
    with TestClient(app) as test_client:
        yield test_client


def indoor_payload() -> dict:
    return {
        "pod_id": "DC_LIBRARY_INDOOR_01",
        "recorded_at": "2026-07-17T18:30:00Z",
        "temperature_c": 23.4,
        "relative_humidity_percent": 48.2,
        "mq135_adc_raw": 1764,
        "mq135_voltage_mv": 1427,
        "battery_voltage_v": 8.3,
        "sensor_warmup_seconds": 7200,
        "wifi_rssi_dbm": -61,
        "response_code": None,
    }


def survey_payload(response_value: int = 4) -> dict:
    return {
        "survey_session_id": "session-123",
        "location_id": "DC_LIBRARY",
        "question_id": "temperature_comfort",
        "response_value": response_value,
    }


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_indoor_insertion(client: TestClient) -> None:
    response = client.post("/api/indoor", json=indoor_payload())
    assert response.status_code == 201
    assert response.json() == {"status": "saved", "id": 1}


def test_invalid_indoor_adc_value(client: TestClient) -> None:
    payload = indoor_payload()
    payload["mq135_adc_raw"] = 4096
    response = client.post("/api/indoor", json=payload)
    assert response.status_code == 422


def test_valid_outdoor_insertion(client: TestClient) -> None:
    response = client.post(
        "/api/outdoor",
        json={
            "location_id": "UNIVERSITY_OF_WATERLOO",
            "temperature_c": 29.4,
            "incoming_radiation_w_m2": 617.2,
            "relative_humidity_percent": 63.0,
        },
    )
    assert response.status_code == 201
    assert response.json()["id"] == 1


def test_valid_survey_answer(client: TestClient) -> None:
    response = client.post(
        "/api/survey-answer",
        json=survey_payload(),
    )
    assert response.status_code == 201
    assert response.json() == {"status": "saved", "id": 1}


def test_survey_answer_outside_range(client: TestClient) -> None:
    response = client.post(
        "/api/survey-answer",
        json=survey_payload(response_value=6),
    )
    assert response.status_code == 422


def test_duplicate_survey_answer_is_updated(client: TestClient) -> None:
    first = client.post(
        "/api/survey-answer",
        json=survey_payload(response_value=2),
    )
    second = client.post(
        "/api/survey-answer",
        json=survey_payload(response_value=5),
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    records = client.get(
        "/api/survey-answers", params={"survey_session_id": "session-123"}
    ).json()
    assert len(records) == 1
    assert records[0]["response_value"] == 5


def test_write_requires_no_authentication(client: TestClient) -> None:
    response = client.post("/api/indoor", json=indoor_payload())
    assert response.status_code == 201


def test_cross_origin_writes_are_allowed(client: TestClient) -> None:
    response = client.options(
        "/api/indoor",
        headers={
            "Origin": "https://survey.example.edu",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_retrieval_of_saved_records(client: TestClient) -> None:
    client.post("/api/indoor", json=indoor_payload())
    second = indoor_payload()
    second["pod_id"] = "OTHER_POD"
    client.post("/api/indoor", json=second)

    response = client.get(
        "/api/indoor", params={"pod_id": "DC_LIBRARY_INDOOR_01"}
    )
    assert response.status_code == 200
    records = response.json()
    assert len(records) == 1
    assert records[0]["pod_id"] == "DC_LIBRARY_INDOOR_01"
    assert records[0]["received_at"].endswith("Z")
