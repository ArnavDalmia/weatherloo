import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# For the deployed API, replace this with: http://YOUR_EXTERNAL_IP
BASE_URL = "http://34.41.103.71".rstrip("/")


def check_health():
    print(f"Checking API connection at {BASE_URL}/health...")

    try:
        with urlopen(f"{BASE_URL}/health", timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))

            print("Health status:", response.status)
            print("Health response:", body)

            if response.status == 200 and body == {"status": "ok"}:
                print("Connection successful.\n")
                return True

            print("The API responded, but the health response was unexpected.")
            return False

    except HTTPError as error:
        print("Health check HTTP error:", error.code)
        print(error.read().decode("utf-8"))
        return False

    except URLError as error:
        print("Health check connection error:", error.reason)
        return False


def post_indoor():
    payload = {
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

    request = Request(
        f"{BASE_URL}/api/indoor",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    send_request(request)


def get_indoor():
    query = urlencode({
        "pod_id": "DC_LIBRARY_INDOOR_01",
        "limit": 10,
    })

    request = Request(
        f"{BASE_URL}/api/indoor?{query}",
        method="GET",
    )

    send_request(request)


def send_request(request):
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")

            print("HTTP status:", response.status)
            print("Response:")
            print(json.dumps(json.loads(body), indent=2))

    except HTTPError as error:
        print("HTTP error:", error.code)
        print(error.read().decode("utf-8"))

    except URLError as error:
        print("Connection error:", error.reason)


if check_health():
    # First run:
    #post_indoor()

    # Second run: comment out post_indoor() and uncomment this:
    get_indoor()
else:
    print("Stopping because the API health check failed.")