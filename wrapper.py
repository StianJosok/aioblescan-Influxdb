import os
import time
import subprocess
import json
from typing import Any, Dict, Optional

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

SEND_INTERVAL_SEC = float(os.getenv("SEND_INTERVAL_SEC", "60"))
DEVICE_KEY_FIELD = os.getenv("DEVICE_KEY_FIELD", "mac")

# Tag only stable identity/dimension keys to avoid high-cardinality issues.
# Color is derived and tagged as "color" automatically.
TAG_KEYS = set(
    k.strip()
    for k in os.getenv("TAG_KEYS", "mac,uuid,addr,peer,color").split(",")
    if k.strip()
)

# Common Tilt/Tilt Pro decoder heuristic:
# Tilt minor ~ 1000-1200; Tilt Pro minor ~ 10000-12000
HD_MINOR_THRESHOLD = int(os.getenv("HD_MINOR_THRESHOLD", "2000"))

# Recognize Tilt family UUID prefix (case-insensitive, dashes removed)
TILT_UUID_PREFIX = os.getenv("TILT_UUID_PREFIX", "a495bb").lower()

# Tilt UUID-to-color mapping (classic Tilt; also used by Tilt Pro colors)
TILT_COLOR_BY_CODE = {
    "10": "red",
    "20": "green",
    "30": "black",
    "40": "purple",
    "50": "orange",
    "60": "blue",
    "70": "yellow",
    "80": "pink",
}


client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)


def device_key(d: Dict[str, Any]) -> Optional[str]:
    return d.get(DEVICE_KEY_FIELD) or d.get("uuid") or d.get("addr") or d.get("peer")


def normalize_uuid(u: Optional[str]) -> str:
    if not u:
        return ""
    return u.replace("-", "").strip().lower()


def tilt_color_from_uuid(u: Optional[str]) -> Optional[str]:
    uu = normalize_uuid(u)
    if not uu.startswith(TILT_UUID_PREFIX):
        return None
    # A495BB{code}...
    if len(uu) >= 8:
        code = uu[6:8]
        return TILT_COLOR_BY_CODE.get(code)
    return None


def add_tilt_normalized_fields(point: Point, data: Dict[str, Any]) -> Point:
    """
    Adds normalized fields without changing existing 'major'/'minor' types:
      - temp_f (float)
      - sg (float)

    Only applies when UUID looks like Tilt (A495BB...).
    """
    uuid = data.get("uuid")
    if not normalize_uuid(uuid).startswith(TILT_UUID_PREFIX):
        return point

    major = data.get("major")
    minor = data.get("minor")
    if not isinstance(major, (int, float)) or not isinstance(minor, (int, float)):
        return point

    is_hd = minor > HD_MINOR_THRESHOLD  # Tilt Pro / HD heuristic

    if is_hd:
        temp_f = float(major) / 10.0
        sg = float(minor) / 10000.0
    else:
        temp_f = float(major)
        sg = float(minor) / 1000.0

    return point.field("temp_f", temp_f).field("sg", sg)


def send_to_influx(data: Dict[str, Any]) -> None:
    point = Point("bluetooth_data")

    # Add color tag (derived from Tilt UUID)
    color = tilt_color_from_uuid(data.get("uuid"))
    if color:
        point = point.tag("color", color)

    # Add normalized numeric fields (temp_f, sg) without touching raw major/minor
    point = add_tilt_normalized_fields(point, data)

    # Write remaining keys with controlled tagging
    for key, value in data.items():
        if key in ("temp_f", "sg"):
            continue

        if isinstance(value, str):
            if key in TAG_KEYS:
                point = point.tag(key, value)
            else:
                point = point.field(key, value)  # keep strings as fields unless explicitly tagged
        elif isinstance(value, bool):
            point = point.field(key, value)
        elif isinstance(value, (int, float)):
            point = point.field(key, value)
        else:
            continue

    write_api.write(bucket=INFLUXDB_BUCKET, record=point)


def main() -> None:
    if not INFLUXDB_TOKEN or not INFLUXDB_ORG or not INFLUXDB_BUCKET:
        raise SystemExit("Missing one of INFLUXDB_TOKEN / INFLUXDB_ORG / INFLUXDB_BUCKET")

    latest_by_device: Dict[str, Dict[str, Any]] = {}
    last_flush = time.monotonic()

    proc = subprocess.Popen(
        ["python3", "-u", "-m", "aioblescan", "-T"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None

    for raw in iter(proc.stdout.readline, b""):
        now = time.monotonic()

        try:
            data = json.loads(raw.decode("utf-8", errors="ignore").strip())
            if isinstance(data, dict):
                k = device_key(data)
                if k:
                    latest_by_device[k] = data
        except Exception:
            pass

        if now - last_flush >= SEND_INTERVAL_SEC:
            if latest_by_device:
                snapshot = list(latest_by_device.values())
                latest_by_device.clear()

                flushed = 0
                for d in snapshot:
                    try:
                        send_to_influx(d)
                        flushed += 1
                    except Exception:
                        pass

                print(f"Flushed {flushed} points to InfluxDB")

            last_flush = now

    for d in latest_by_device.values():
        try:
            send_to_influx(d)
        except Exception:
            pass


if __name__ == "__main__":
    main()
