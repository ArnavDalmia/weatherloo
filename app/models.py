"""SQLite schema and table metadata."""

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS indoor_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pod_id TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        received_at TEXT NOT NULL,
        temperature_c REAL NOT NULL,
        relative_humidity_percent REAL NOT NULL,
        mq135_adc_raw INTEGER NOT NULL,
        mq135_voltage_mv INTEGER NOT NULL,
        battery_voltage_v REAL,
        sensor_warmup_seconds INTEGER,
        wifi_rssi_dbm INTEGER,
        response_code INTEGER,
        CHECK (relative_humidity_percent BETWEEN 0 AND 100),
        CHECK (mq135_adc_raw BETWEEN 0 AND 4095),
        CHECK (mq135_voltage_mv >= 0),
        CHECK (battery_voltage_v IS NULL OR battery_voltage_v >= 0),
        CHECK (sensor_warmup_seconds IS NULL OR sensor_warmup_seconds >= 0),
        CHECK (response_code IS NULL OR response_code IN (1, 2, 3))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS outdoor_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_id TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        received_at TEXT NOT NULL,
        temperature_c REAL NOT NULL,
        incoming_radiation_w_m2 REAL,
        humidex REAL,
        relative_humidity_percent REAL NOT NULL,
        dew_point_c REAL,
        CHECK (relative_humidity_percent BETWEEN 0 AND 100),
        CHECK (
            incoming_radiation_w_m2 IS NULL
            OR incoming_radiation_w_m2 >= 0
        )
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS survey_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        survey_session_id TEXT NOT NULL,
        location_id TEXT NOT NULL,
        pod_id TEXT,
        question_id TEXT NOT NULL,
        response_value INTEGER NOT NULL,
        answered_at TEXT NOT NULL,
        received_at TEXT NOT NULL,
        CHECK (response_value BETWEEN 1 AND 5),
        UNIQUE (survey_session_id, question_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_indoor_recorded_at ON indoor_readings(recorded_at)",
    "CREATE INDEX IF NOT EXISTS idx_indoor_pod_id ON indoor_readings(pod_id)",
    "CREATE INDEX IF NOT EXISTS idx_outdoor_recorded_at ON outdoor_readings(recorded_at)",
    "CREATE INDEX IF NOT EXISTS idx_outdoor_location_id ON outdoor_readings(location_id)",
    "CREATE INDEX IF NOT EXISTS idx_survey_answered_at ON survey_answers(answered_at)",
    "CREATE INDEX IF NOT EXISTS idx_survey_location_id ON survey_answers(location_id)",
    "CREATE INDEX IF NOT EXISTS idx_survey_pod_id ON survey_answers(pod_id)",
    "CREATE INDEX IF NOT EXISTS idx_survey_session_id ON survey_answers(survey_session_id)",
)

TABLE_COLUMNS = {
    "indoor_readings": (
        "id",
        "pod_id",
        "recorded_at",
        "received_at",
        "temperature_c",
        "relative_humidity_percent",
        "mq135_adc_raw",
        "mq135_voltage_mv",
        "battery_voltage_v",
        "sensor_warmup_seconds",
        "wifi_rssi_dbm",
        "response_code",
    ),
    "outdoor_readings": (
        "id",
        "location_id",
        "recorded_at",
        "received_at",
        "temperature_c",
        "incoming_radiation_w_m2",
        "humidex",
        "relative_humidity_percent",
        "dew_point_c",
    ),
    "survey_answers": (
        "id",
        "survey_session_id",
        "location_id",
        "pod_id",
        "question_id",
        "response_value",
        "answered_at",
        "received_at",
    ),
}
