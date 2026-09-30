FROM python:3.12-slim

WORKDIR /app

COPY requirements-custom-receiver.txt .
RUN pip install --no-cache-dir -r requirements-custom-receiver.txt

COPY custom_event_receiver.py .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "custom_event_receiver:app"]
