# Build context é a raiz do repositório (ver docker-compose.yml) porque este Dockerfile
# precisa copiar tanto engine/ quanto backend/ — a engine é instalada como dependência
# editável local, nunca reescrita ou empacotada separadamente.
FROM python:3.12-slim

# Libs nativas exigidas pelo WeasyPrint (Pango/Cairo/GDK-Pixbuf) para renderizar os PDFs
# executivo/detalhado — sem isso o import de gera_d_engine.rendering falha em runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    libffi8 \
    fonts-liberation \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY engine/ /engine/
COPY backend/ /app/

RUN pip install --no-cache-dir -e /engine -e ".[dev]"

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
