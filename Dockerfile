# Base Image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (including libcap2-bin for setcap)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-distutils \
    bluez \
    unzip \
    libcap2-bin \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install aioblescan Tilt module
ADD https://github.com/baronbrew/aioblescan/archive/master.zip /tmp/aioblescan.zip
RUN unzip /tmp/aioblescan.zip -d /tmp && \
    cd /tmp/aioblescan-master && \
    python3 setup.py install && \
    rm -rf /tmp/aioblescan*

# Install Python InfluxDB client
RUN pip install influxdb-client

# Add the wrapper script
RUN echo "\
import os\n\
import subprocess\n\
import json\n\
from influxdb_client import InfluxDBClient, Point\n\
from influxdb_client.client.write_api import SYNCHRONOUS\n\
\n\
# InfluxDB configuration\n\
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')\n\
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')\n\
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')\n\
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET')\n\
\n\
# Initialize InfluxDB client\n\
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)\n\
write_api = client.write_api(write_options=SYNCHRONOUS)\n\
\n\
def send_to_influx(data):\n\
    try:\n\
        point = Point('bluetooth_data')\n\
        for key, value in data.items():\n\
            if isinstance(value, str):\n\
                point = point.tag(key, value)\n\
            else:\n\
                point = point.field(key, value)\n\
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)\n\
        print(f'Sent to InfluxDB: {data}')\n\
    except Exception as e:\n\
        print(f'Error sending to InfluxDB: {e}')\n\
\n\
# Run aioblescan and process output\n\
def main():\n\
    process = subprocess.Popen(['python3', '-u', '-m', 'aioblescan', '-T'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)\n\
    for line in iter(process.stdout.readline, b''):\n\
        try:\n\
            line = line.decode('utf-8').strip()\n\
            data = json.loads(line)\n\
            send_to_influx(data)\n\
        except json.JSONDecodeError:\n\
            print(f'Could not decode line: {line}')\n\
        except Exception as e:\n\
            print(f'Error processing line: {e}')\n\
\n\
if __name__ == '__main__':\n\
    main()\n\
" > /app/wrapper.py

# Expose Bluetooth interface permissions
RUN setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))

# Ensure Bluetooth is up and run the wrapper script
CMD ["bash", "-c", "hciconfig hci0 up && python3 /app/wrapper.py"]