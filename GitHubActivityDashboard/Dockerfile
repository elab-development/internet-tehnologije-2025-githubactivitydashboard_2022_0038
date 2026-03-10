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
# # Primer za Linux container
# RUN curl -sSL https://reflex.run/install.sh | bash

# # Dodaj reflex u PATH
# ENV PATH="/root/.reflex/bin:${PATH}"

# # Sada inicijalizuj projekat
# RUN reflex init
# # Inicijalizuj Reflex projekat
# rxconfig.py mora biti u /app/ root-u, ne u subfoldera
RUN cp ./GitHubActivityDashboard/rxconfig.py ./rxconfig.py

RUN reflex init
EXPOSE 3000 8000

CMD ["reflex", "run", "--env", "prod", "--loglevel", "info"]

