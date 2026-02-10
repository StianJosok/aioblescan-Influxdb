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

# Tag only stable identity/dimension keys to avoid high-cardinality issues
# You can override with env var: TAG_KEYS="mac,uuid,addr,peer,color,model"
TAG_KEYS = set(
    k.strip()
    for k in os.getenv("TAG_KEYS", "mac,uuid,addr,peer,color,model").split(",")
    if k.strip()
)

# Heuristic threshold used by common Tilt decoders (including Node-RED flows):
# Tilt (classic) minor ~ 1000-1200; Tilt Pro (HD) minor ~ 10000-12000
HD_MINOR_THRESHOLD = int(os.getenv("HD_MINOR_THRESHOLD", "2000"))

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)


def device_key(d: Dict[str, Any]) -> Optional[str]:
    return d.get(DEVICE_KEY_FIELD) or d.get("uuid") or d.get("addr") or d.get("peer")


def add_tilt_normalized_fields(point: Point, data: Dict[str, Any]) -> Point:
    """
    Adds normalized fields without changing existing 'major'/'minor' types.
    Adds:
      - temp_f (float)
      - sg (float)
      - hd (bool)
      - model (tag: tilt / tilt_pro)
    """
    major = data.get("major")
    minor = data.get("minor")

    if not isinstance(major, (int, float)) or not isinstance(minor, (int, float)):
        return point

    is_hd = minor > HD_MINOR_THRESHOLD

    if is_hd:
        temp_f = float(major) / 10.0
        sg = float(minor) / 10000.0
        point = point.tag("model", "tilt_pro").field("hd", True)
    else:
        temp_f = float(major)
        sg = float(minor) / 1000.0
        point = point.tag("model", "tilt").field("hd", False)

    point = point.field("temp_f", temp_f).field("sg", sg)
    return point


def send_to_influx(data: Dict[str, Any]) -> None:
    point = Point("bluetooth_data")

    # Add normalized fields first (does not alter raw major/minor)
    point = add_tilt_normalized_fields(point, data)

    # Write remaining keys with controlled tagging
    for key, value in data.items():
        # Avoid duplicating fields we add ourselves
        if key in ("temp_f", "sg", "hd"):
            continue

        # Only tag stable keys; write other strings as string fields
        if isinstance(value, str):
            if key in TAG_KEYS:
                point = point.tag(key, value)
            else:
                point = point.field(key, value)
        elif isinstance(value, bool):
            point = point.field(key, value)
        elif isinstance(value, (int, float)):
            point = point.field(key, value)
        else:
            # Ignore nested dict/list/etc.
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

    # final flush
    for d in latest_by_device.values():
        try:
            send_to_influx(d)
        except Exception:
            pass


if __name__ == "__main__":
    main()
