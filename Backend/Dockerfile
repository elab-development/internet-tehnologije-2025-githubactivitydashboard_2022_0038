FROM python:3.11-slim

WORKDIR /app

# Sistemske zavisnosti
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Python zavisnosti
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root korisnik (bezbednost)
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser /app
USER appuser

EXPOSE 5000

# Gunicorn za produkciju
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]