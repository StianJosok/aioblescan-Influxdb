# Base Image
FROM python:3.9-slim-bookworm

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
COPY wrapper.py /app/wrapper.py

# Expose Bluetooth interface permissions
RUN setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))

# Ensure Bluetooth is up and run the wrapper script
CMD ["bash", "-c", "hciconfig hci0 up && python3 /app/wrapper.py"]
