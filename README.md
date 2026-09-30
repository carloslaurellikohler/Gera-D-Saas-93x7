# GerAD

SaaS de análise de conversas com metodologia 93x7®. Upload de transcrição/áudio/vídeo →
transcrição (quando necessário) → análise via IA → relatórios executivo e detalhado,
com acompanhamento assíncrico do processamento.

## Arquitetura

```
Presentation (frontend React)
   ↓ HTTP
API / Application (FastAPI)
   ↓
Domain / Orchestration (AnalysisService)
   ↓
Processing (worker Celery)
   ↓
Infrastructure (engine gera_d_engine, Postgres, storage local)
```

- `engine/` — motor de análise (`gera_d_engine`), pacote Python isolado e intocado por este
  trabalho. Roda hoje via CLI (`python -m gera_d_engine.cli analyze ...`); ver `engine/README.md`.
- `backend/` — API FastAPI + orquestração + persistência + worker assíncrono, construídos ao
  redor da engine (nunca a modificando).
- `frontend/` — SPA React + TypeScript.

## Formatos de entrada suportados

A engine despacha ingestão por extensão de arquivo e hoje só reconhece **`.docx`, `.txt`,
`.mp3`, `.mp4`** (`gera_d_engine.ingestion.loader`). **`.wav` e `.m4a` não são aceitos** —
isso é uma limitação atual da engine, não do backend; enviar esses formatos retorna um erro
4xx claro na API, nunca um 500. Ver plano de arquitetura para o racional de não contornar
isso silenciosamente com transcodificação.

## Desenvolvimento local — backend

Pré-requisitos: Python ≥3.11, Postgres, Redis.

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -e ".[dev]"
./.venv/bin/pip install -e ../engine   # engine como dependência editável local

cp .env.example .env   # ajuste DATABASE_URL/REDIS_URL/OPENAI_API_KEY etc.
./.venv/bin/alembic upgrade head

# API
./.venv/bin/uvicorn app.main:app --reload --port 8000

# Worker (processo separado)
./.venv/bin/celery -A app.workers.celery_app worker --loglevel=info
```

Testes (rápidos, sem chamar a OpenAI — a suíte padrão já exclui os testes `slow`):

```bash
./.venv/bin/pytest
```

Teste de integração real contra a OpenAI (custo real de API, nunca roda por padrão):

```bash
GERAD_RUN_ENGINE_SMOKE_TEST=1 ./.venv/bin/pytest -m slow
```

### Nota sobre `OPENAI_API_KEY` e `.env` fora de Docker

A engine (`gera_d_engine.config`) carrega seu próprio `.env` via `python-dotenv` na
importação. Rodando o backend fora de container, essa descoberta é sensível ao contexto de
execução (`python -c` vs. `pytest`, por exemplo) e pode ou não enxergar `engine/.env` mesmo
com o processo rodando a partir de `backend/`. **Não confie nisso** — defina
`OPENAI_API_KEY`/`OPENAI_MODEL`/`OPENAI_TEMPERATURE` explicitamente em `backend/.env` (como no
`.env.example`) ou exporte-os no ambiente. Dentro do Docker Compose isso não é um problema:
as variáveis chegam ao container só via `environment:`, nunca por descoberta implícita de
arquivo.

## Desenvolvimento local — frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Testes (Vitest + Testing Library, não precisam de navegador real):

```bash
npm run test
```

## Docker Compose

Sobe os 5 serviços (`postgres`, `redis`, `backend`, `worker`, `frontend`):

```bash
cp .env.example .env   # ajuste OPENAI_API_KEY e demais valores
docker compose up --build
```

- Backend: http://localhost:8000 (`/health`, `/api/v1/analyses`, docs em `/docs`)
- Frontend: http://localhost:5173
- `postgres`/`redis` não expõem portas para o host — só a rede interna do Compose.
- `backend` roda `alembic upgrade head` automaticamente antes de subir o Uvicorn.
- `worker` só inicia depois que `backend` fica saudável (garante que as migrations já rodaram).
- O volume nomeado `storage_data` é compartilhado entre `backend` e `worker` — é assim que o
  worker (processo/container separado) consegue ler o arquivo que a API salvou no upload.
