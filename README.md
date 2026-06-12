# Aioblescan with InfluxDB Integration

This project provides a self-contained Docker image for scanning Bluetooth signals using `aioblescan` and forwarding the data to InfluxDB.

## Features
- Uses [`aioblescan`](https://github.com/frawau/aioblescan) with its Tilt plugin to scan for Bluetooth signals.
- Parses the output and sends the data to an InfluxDB bucket.
- Configurable using environment variables.

## Usage

### Run the Container
```bash
docker run --rm \
  --name aioblescan-influx \
  --network host \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  -e INFLUXDB_URL="https://influx.example.com" \
  -e INFLUXDB_TOKEN="your-influxdb-token" \
  -e INFLUXDB_ORG="your-org" \
  -e INFLUXDB_BUCKET="your-bucket" \
  -e SEND_INTERVAL_SEC="60" \
  -e DEVICE_KEY_FIELD="mac" \
  -e LOG_LEVEL=INFO \
  stianjosok/aioblescan-influxdb:latest

```
## Docker Compose
```yaml
services:
  aioblescan-influx:
    image: stianjosok/aioblescan-influxdb:latest
    container_name: aioblescan-influx
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    environment:
      - INFLUXDB_URL=${INFLUXDB_URL}
      - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
      - INFLUXDB_ORG=${INFLUXDB_ORG}
      - INFLUXDB_BUCKET=${INFLUXDB_BUCKET}
      - SEND_INTERVAL_SEC=60
      - DEVICE_KEY_FIELD=mac   # or uuid/addr/peer
      - LOG_LEVEL=INFO
    restart: unless-stopped
```

### .env File
```.env
INFLUXDB_URL=http://<INFLUXDB_HOST>:8086
INFLUXDB_TOKEN=your-influxdb-token
INFLUXDB_ORG=your-org
INFLUXDB_BUCKET=your-bucket
LOG_LEVEL=INFO
```

### Required capabilities
The image grants `cap_net_raw,cap_net_admin` to the Python binary via file
capabilities, so the container must run with `--cap-add=NET_ADMIN` and
`--cap-add=NET_RAW` (as in the examples above). Without them, Python fails
to start with `operation not permitted`.

## Credits
- [Baron Brew](https://github.com/baronbrew) wrote the original Tilt plugin for
  `aioblescan` (since merged upstream). Their work inspired this project — and
  got me far more involved with GitHub and open source than I would have been
  otherwise.
- [François Wautier](https://github.com/frawau) is the author and maintainer of
  [`aioblescan`](https://github.com/frawau/aioblescan), which this image uses
  via PyPI.
