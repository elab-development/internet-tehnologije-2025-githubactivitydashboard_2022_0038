FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    nodejs \
    npm \
    unzip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./GitHubActivityDashboard/
RUN cp ./GitHubActivityDashboard/rxconfig.py ./rxconfig.py

RUN reflex init
EXPOSE 3000 8000

CMD ["reflex", "run", "--env", "prod", "--loglevel", "info"]

