# Build context é a raiz do repositório (ver docker-compose.yml) porque este Dockerfile
# precisa copiar tanto engine/ quanto backend/ — a engine é instalada como dependência
# editável local, nunca reescrita ou empacotada separadamente.
FROM python:3.12-slim

# Libs nativas exigidas pelo WeasyPrint (Pango/Cairo/GDK-Pixbuf) para renderizar os PDFs
# executivo/detalhado — sem isso o import de gera_d_engine.rendering falha em runtime.
# ffmpeg é usado por app/engine_integration/audio_chunking.py para contornar o limite de
# 25MB por arquivo da API Whisper em uploads de áudio/vídeo grandes.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    libffi8 \
    fonts-liberation \
    shared-mime-info \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY engine/ /engine/
COPY backend/ /app/
# metodologia_93x7.pdf é a única fonte do corpus do Assistente de IA (Fase 6), lido por
# scripts/ingest_methodology.py — copiado à parte (não docs/ inteiro) para não levar os
# exemplos/handoff que também vivem em docs/ para a imagem.
COPY docs/metodologia_93x7.pdf /docs/metodologia_93x7.pdf

RUN pip install --no-cache-dir -e /engine -e ".[dev]"

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
