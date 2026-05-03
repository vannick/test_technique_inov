FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dépendances Python
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Code applicatif
COPY . .

# Dossier persistant pour SQLite
RUN mkdir -p /app/data

# Créer les dossiers de logs
RUN mkdir -p /app/logs

EXPOSE 8000

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
