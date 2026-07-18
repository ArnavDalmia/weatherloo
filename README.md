# University Environmental Sensing API

A small FastAPI service that stores indoor sensor snapshots, outdoor
environmental snapshots, and individual student survey answers in a persistent
SQLite database.

## Architecture

The ESP32, outdoor data source, and survey web app send independent HTTP POST
requests to one FastAPI process. FastAPI validates each request with Pydantic
and writes it to one of three SQLite tables:

- `indoor_readings`: append-only, complete indoor snapshots
- `outdoor_readings`: append-only, complete outdoor snapshots
- `survey_answers`: one row per question answer

Survey rows are grouped by `survey_session_id`. A partial survey is useful
immediately; it does not need all five answers. Resubmitting the same
`survey_session_id` and `question_id` updates that row, allowing a student to
change a selection.

The application creates the database directory and tables at startup. SQLite
uses WAL mode, a busy timeout, parameterized SQL, and one connection per
operation. Times are stored as ISO 8601 UTC strings such as
`2026-07-17T18:30:00Z`. A timestamp without an offset is interpreted as UTC.

## Local setup

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
```

Activate the environment:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Install dependencies and configure the current shell:

```bash
pip install -r requirements.txt
```

```powershell
# Windows PowerShell
$env:DATABASE_PATH = "data/project.db"
```

```bash
# Linux/macOS
export DATABASE_PATH="data/project.db"
```

`.env.example` documents the variables, but the application intentionally
reads the process environment directly. Do not commit a real `.env` file.

Start the development server:

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation.

## Environment variables

- `DATABASE_PATH`: optional; defaults to `data/project.db`
- `PORT`: used by `start.sh`; defaults to `8000`

All endpoints are public and require no authentication. Cross-origin requests
are allowed from any website. Request bodies must still match the documented
schema and validation ranges.

## Endpoints

- `GET /health`
- `POST /api/indoor`
- `POST /api/outdoor`
- `POST /api/survey-answer`
- `GET /api/indoor`
- `GET /api/outdoor`
- `GET /api/survey-answers`
- `GET /api/export/indoor.csv`
- `GET /api/export/outdoor.csv`
- `GET /api/export/survey-answers.csv`

List endpoints return newest records first and accept `limit` (default 100,
maximum 1000), `start_time`, and `end_time`. Indoor supports `pod_id`; outdoor
supports `location_id`; survey answers support `survey_session_id`,
`location_id`, and `pod_id`. Time filters apply to `recorded_at` or
`answered_at`, as appropriate.

## Example requests

Indoor snapshot:

```bash
curl -X POST http://127.0.0.1:8000/api/indoor \
  -H "Content-Type: application/json" \
  -d '{
    "pod_id": "DC_LIBRARY_INDOOR_01",
    "recorded_at": "2026-07-17T18:30:00Z",
    "temperature_c": 23.4,
    "relative_humidity_percent": 48.2,
    "mq135_adc_raw": 1764,
    "mq135_voltage_mv": 1427,
    "battery_voltage_v": 8.3,
    "sensor_warmup_seconds": 7200,
    "wifi_rssi_dbm": -61,
    "response_code": null
  }'
```

Outdoor snapshot:

```bash
curl -X POST http://127.0.0.1:8000/api/outdoor \
  -H "Content-Type: application/json" \
  -d '{
    "location_id": "UNIVERSITY_OF_WATERLOO",
    "recorded_at": "2026-07-17T18:30:00Z",
    "temperature_c": 29.4,
    "incoming_radiation_w_m2": 617.2,
    "humidex": 35.1,
    "relative_humidity_percent": 63.0,
    "dew_point_c": 21.4
  }'
```

One survey answer:

```bash
curl -X POST http://127.0.0.1:8000/api/survey-answer \
  -H "Content-Type: application/json" \
  -d '{
    "survey_session_id": "550e8400-e29b-41d4-a716-446655440000",
    "location_id": "DC_LIBRARY",
    "pod_id": "DC_LIBRARY_INDOOR_01",
    "question_id": "temperature_comfort",
    "response_value": 4,
    "answered_at": "2026-07-17T18:31:10Z"
  }'
```

Send more questions as separate requests with the same
`survey_session_id`. Question IDs are not hard-coded.

Retrieve and filter records:

```bash
curl "http://127.0.0.1:8000/api/indoor?pod_id=DC_LIBRARY_INDOOR_01&limit=20"
curl "http://127.0.0.1:8000/api/outdoor?location_id=UNIVERSITY_OF_WATERLOO"
curl "http://127.0.0.1:8000/api/survey-answers?survey_session_id=550e8400-e29b-41d4-a716-446655440000"
```

## Database and CSV access

Install the SQLite CLI if needed, then inspect the database:

```bash
sqlite3 data/project.db
.tables
.schema survey_answers
SELECT * FROM indoor_readings ORDER BY received_at DESC LIMIT 10;
```

Download complete CSV exports:

```bash
curl -OJ http://127.0.0.1:8000/api/export/indoor.csv
curl -OJ http://127.0.0.1:8000/api/export/outdoor.csv
curl -OJ http://127.0.0.1:8000/api/export/survey-answers.csv
```

The database, WAL, and shared-memory files under `data/` are ignored by Git.
Back up all three consistently, or stop the service and copy `project.db`.

## Tests

Tests use a separate temporary database:

```bash
pytest -q
```

## Deploy to a DigitalOcean Ubuntu Droplet

1. Create an Ubuntu Droplet, add an SSH key, and allow inbound SSH. For initial
   testing, also allow TCP port 8000 in the DigitalOcean firewall.
2. Install system packages:

   ```bash
   sudo apt update
   sudo apt install -y python3-venv python3-pip git sqlite3
   ```

3. Clone the GitHub repository and install the application:

   ```bash
   sudo mkdir -p /opt/environment-api
   sudo chown "$USER":"$USER" /opt/environment-api
   git clone https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git /opt/environment-api
   cd /opt/environment-api
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   mkdir -p data
   chmod +x start.sh
   ```

4. Create `/etc/environment-api` as root:

   ```ini
   DATABASE_PATH=/opt/environment-api/data/project.db
   PORT=8000
   ```

   Protect it with `sudo chmod 600 /etc/environment-api`.

5. Create `/etc/systemd/system/environment-api.service`:

   ```ini
   [Unit]
   Description=University environmental sensing API
   After=network.target

   [Service]
   Type=simple
   User=YOUR_LINUX_USER
   Group=YOUR_LINUX_USER
   WorkingDirectory=/opt/environment-api
   EnvironmentFile=/etc/environment-api
   ExecStart=/opt/environment-api/start.sh
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

6. Start and verify the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now environment-api
   sudo systemctl status environment-api
   curl http://DROPLET_IP:8000/health
   ```

The public API is now reachable at the Droplet IP on port 8000.

For real use, point a domain at the Droplet, install Nginx, proxy HTTPS traffic
to `127.0.0.1:8000`, and obtain a certificate:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo certbot --nginx -d api.example.edu
```

After Nginx is working, bind Uvicorn to `127.0.0.1` in `start.sh`, close public
port 8000, and leave only ports 22, 80, and 443 open. Configure Nginx request
size and rate limits appropriate to the project.

### Updating the deployment

Push changes to GitHub, then on the Droplet:

```bash
cd /opt/environment-api
git pull --ff-only
.venv/bin/pip install -r requirements.txt
sudo systemctl restart environment-api
sudo systemctl status environment-api
curl http://127.0.0.1:8000/health
```

The database remains at `/opt/environment-api/data/project.db` and is not
changed by `git pull`. Take regular off-Droplet backups of that file.
