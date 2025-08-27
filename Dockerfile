FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Системные зависимости (по необходимости расширишь)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# requirements.txt должен лежать рядом с Dockerfile
COPY requirements.txt .
RUN pip install -U pip && pip install -r requirements.txt

# Копируем проект
COPY tg_agregator .

# По умолчанию — пусть ничего не делает (команды зададим в compose)
CMD ["python", "-V"]
