FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install deps, use, and clean up in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    bluez \
    libcap2-bin \
    curl \
    unzip \
    && curl -L https://github.com/baronbrew/aioblescan/archive/60b9fdb99019eae94d8031c4627a54debb4dd7c6.zip -o /tmp/aioblescan.zip \
    && unzip /tmp/aioblescan.zip -d /tmp \
    && apt-get remove -y unzip curl \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/aioblescan.zip

WORKDIR /app

COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir /tmp/aioblescan-60b9fdb99019eae94d8031c4627a54debb4dd7c6 \
    && rm -rf /tmp/aioblescan-60b9fdb99019eae94d8031c4627a54debb4dd7c6

COPY wrapper.py /app/wrapper.py

# Grant BLE capabilities to python
RUN setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))

CMD ["bash", "-c", "hciconfig hci0 up && exec python3 /app/wrapper.py"]