# Aioblescan with InfluxDB Integration

This project provides a self-contained Docker image for scanning Bluetooth signals using `aioblescan` and forwarding the data to InfluxDB.

## Features
- Uses `aioblescan` with the Tilt plugin to scan for Bluetooth signals.
- Parses the output and sends the data to an InfluxDB bucket.
- Configurable using environment variables.

## Usage
### Clone the repository
```bash
git clone https://github.com/StianJosok/aioblescan-Influxdb.git
```
### Build the Image
```bash
docker build -t aioblescan-influx:latest .
```
### Run the Container
```bash
docker run --rm \
  --name aioblescan-influx \
  --network host \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  -e INFLUXDB_URL="https://influx.sjnorway.com" \
  -e INFLUXDB_TOKEN="your-influxdb-token" \
  -e INFLUXDB_ORG="sjhomelab" \
  -e INFLUXDB_BUCKET="beer" \
  -e SEND_INTERVAL_SEC="60" \
  -e DEVICE_KEY_FIELD="mac" \
  aioblescan-influx

```
## Docker Compose
```yaml
services:
  aioblescan-influx:
    image: aioblescan-influx:latest
    container_name: aioblescan-influx
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    environment:
      - INFLUXDB_URL=${INFLUXDB_URL}
      - INFLUXDB_TOKEN=${INFLUX_TOKEN}
      - INFLUXDB_ORG=${INFLUXDB_ORG}
      - INFLUXDB_BUCKET=${INFLUXDB_BUCKET}
      - SEND_INTERVAL_SEC=60
      - DEVICE_KEY_FIELD=mac   # or uuid/addr/peer depending on your aioblescan JSO
    restart: unless-stopped
```

### .env File
```.env
INFLUXDB_URL=http://<INFLUXDB_HOST>:8086
INFLUXDB_TOKEN=your-influxdb-token
INFLUXDB_ORG=your-org
INFLUXDB_BUCKET=your-bucket
```
