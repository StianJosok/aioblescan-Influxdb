FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    bluez \
    libcap2-bin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY wrapper.py /app/wrapper.py

# Grant BLE capabilities to python
RUN setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))

CMD ["bash", "-c", "hciconfig hci0 up && exec python3 /app/wrapper.py"]
