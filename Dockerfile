FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install deps, use, and clean up in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    bluez \
    libcap2-bin \
    curl \
    unzip \
    && curl -L https://github.com/baronbrew/aioblescan/archive/master.zip -o /tmp/aioblescan.zip \
    && unzip /tmp/aioblescan.zip -d /tmp \
    && apt-get remove -y unzip curl \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/aioblescan.zip

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir setuptools influxdb-client \
    && pip install --no-cache-dir /tmp/aioblescan-master \
    && rm -rf /tmp/aioblescan-master

COPY wrapper.py /app/wrapper.py

# Grant BLE capabilities to python
RUN setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))

CMD ["bash", "-c", "hciconfig hci0 up && python3 /app/wrapper.py"]