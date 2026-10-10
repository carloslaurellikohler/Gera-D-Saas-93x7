# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

O repositório é escrito em português (código, comentários, mensagens de erro, commits).
Mantenha esse idioma em código novo e em commits (`feat:`/`fix:` + descrição em pt-BR).

Decisões arquiteturais já fechadas, que não devem ser reabertas sem motivo forte: engine
intocada, auth stateless, sem autocadastro, sem transcodificação de áudio, nota geral nunca por
fórmula, testes de repositório em Postgres real.

## Três pacotes, uma regra de ouro

```
engine/    pacote Python `gera_d_engine` — NUNCA modificado por trabalho de backend/frontend
backend/   FastAPI + Celery + SQLAlchemy/Alembic, construído AO REDOR da engine
frontend/  SPA React 19 + TS + Vite
```

A engine é tratada como dependência externa instalada em modo editável. Só
`backend/app/engine_integration/` importa `gera_d_engine`; rotas e services nunca importam a
engine direto. O contrato da API pública da engine (assinaturas + campos obrigatórios dos schemas
pydantic) é travado por `backend/tests/contract/test_engine_contract.py` — se esse teste quebrar,
a engine mudou e o adapter precisa acompanhar.

## Comandos

**O projeto roda via Docker Compose** — é assim que se sobe o ambiente de desenvolvimento, e é o
caminho a assumir por padrão. Rodar backend/worker/frontend direto no host é alternativa de
depuração pontual, não o fluxo normal.

### Docker Compose (5 serviços: postgres, redis, backend, worker, frontend)

```bash
cp .env.example .env                 # OPENAI_API_KEY é obrigatória para o pipeline funcionar
docker compose up --build            # --build quando Dockerfile/dependências/código mudarem
docker compose up -d                 # subir em background
docker compose logs -f backend worker
docker compose restart backend
docker compose down                  # `-v` também apaga pgdata/redisdata/storage_data
```

Backend em :8000 (`/docs`), frontend em :5173. `postgres`/`redis` não expõem portas no host —
todo acesso a banco/fila passa por `docker compose exec`.

O fonte é **copiado** nas imagens (não há bind mount), e o `backend` sobe uvicorn sem `--reload`:
mudança em `backend/`, `engine/` ou `frontend/` só aparece depois de
`docker compose up --build <serviço>`.

Comandos dentro dos containers:

```bash
docker compose exec backend python -m scripts.seed_admin          # bootstrap do 1º ADMIN (idempotente)
docker compose exec backend python -m scripts.ingest_methodology  # corpus RAG do assistente
docker compose exec backend alembic upgrade head
docker compose exec backend pytest                                # suíte padrão (addopts exclui `slow`)
docker compose exec backend pytest tests/unit/test_analysis_service.py::test_nome -x
docker compose exec postgres psql -U gerad -d gerad
docker compose exec frontend npm run lint
docker compose exec frontend npm run test
```

Migration nova é melhor gerar pelo venv local: criada via `exec` ela nasce dentro do container e
se perde no próximo build (ou copie de volta com
`docker compose cp backend:/app/alembic/versions/<arquivo> backend/alembic/versions/`).

O `backend` roda `alembic upgrade head` no CMD; o `worker` só sobe depois do healthcheck do
backend (garante migrations aplicadas). O volume `storage_data` é compartilhado entre `backend` e
`worker` — é assim que o worker lê o arquivo que a API gravou no upload.

Os testes exigem **Postgres real** — `tests/conftest.py` cria e dropa o banco `gerad_test`
derivado do host de `DATABASE_URL`; nunca SQLite. Dentro do compose isso já está satisfeito.

`alembic/env.py` importa todos os módulos de `app/models/` explicitamente para popular
`Base.metadata` — ao criar um modelo novo, adicione o import lá **e** em `tests/conftest.py`,
senão a tabela não existe nem na migration autogerada nem nos testes.

Não há ruff/black/mypy configurados no backend. Siga o estilo existente: `from __future__ import
annotations`, type hints completos, docstring de módulo explicando o *porquê* da camada.

### Backend fora do Docker (alternativa de depuração)

Exige Postgres e Redis alcançáveis do host — os do compose não publicam portas.

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -e ".[dev]"
./.venv/bin/pip install -e ../engine      # engine como dependência editável
cp .env.example .env

./.venv/bin/alembic upgrade head
./.venv/bin/uvicorn app.main:app --reload --port 8000
./.venv/bin/celery -A app.workers.celery_app worker --loglevel=info   # processo separado

./.venv/bin/python -m scripts.seed_admin            # bootstrap do 1º ADMIN (idempotente)
./.venv/bin/python -m scripts.ingest_methodology    # corpus RAG do assistente (rodar quando o PDF mudar)
```

Testes e migrations:

```bash
./.venv/bin/pytest                                           # suíte padrão (addopts já exclui `slow`)
./.venv/bin/pytest tests/unit/test_analysis_service.py       # um arquivo
./.venv/bin/pytest tests/unit/test_analysis_service.py::test_nome -x
GERAD_RUN_ENGINE_SMOKE_TEST=1 ./.venv/bin/pytest -m slow     # chama a OpenAI de verdade (custo real)

./.venv/bin/alembic revision --autogenerate -m "descricao"    # caminho preferido para migration nova
```

### Frontend fora do Docker (alternativa de depuração)

```bash
cd frontend
npm install && cp .env.example .env
npm run dev
npm run lint                      # oxlint
npm run build                     # tsc -b && vite build
npm run test                      # vitest run (jsdom)
npx vitest run src/routes/LoginPage.test.tsx    # um arquivo
```

## Arquitetura do backend

Camadas, de fora para dentro — cada uma só conhece a seguinte:

```
api/routes/*.py      HTTP: valida entrada, traduz exceções de domínio → HTTPException, nada de regra
api/deps.py          injeção de dependência: monta TODOS os services (repos + storage + settings)
services/*.py        regra de negócio; levanta exceções de domínio próprias (ValueError-derived)
repositories/*.py    acesso a dados; recebe `Session` no construtor, faz commit/refresh
models/*.py          SQLAlchemy ORM
schemas/*.py         pydantic de request/response (nunca reusa modelo ORM na borda)
```

`api/deps.py` é o ponto único de montagem. Service novo → factory `get_<x>_service` lá, e override
correspondente em `tests/api/conftest.py::_overrides`.

Erros de domínio viram HTTP só na rota: 404 para "não encontrado", **409 para conflito de estado**
(ex.: material ainda referenciado por trilha, publicar rascunho inválido), 503 quando não há
metodologia publicada. Nunca vaze `str(exc)` da engine para o cliente — `AnalysisService._SAFE_MESSAGES`
tem a mensagem segura por etapa.

### Pipeline assíncrono de análise

`POST /analyses` grava o arquivo no storage, cria a `Analysis` e enfileira
`process_analysis_task.delay(id)`; o worker chama `AnalysisService.run_analysis_job`, que avança a
máquina de status `CREATED → UPLOADED → TRANSCRIBING → TRANSCRIBED → ANALYZING →
GENERATING_REPORTS → COMPLETED` (ou `FAILED`). O frontend acompanha por polling
(`useAnalysisStatus`, 2s, para em `COMPLETED`/`FAILED`).

Em `workers/tasks.py`, **só erros transitórios da OpenAI** (`RateLimitError`, `APITimeoutError`,
`APIConnectionError`) fazem retry; falha determinística (arquivo inválido, schema, WeasyPrint) vai
direto para `FAILED` sem queimar créditos.

Formatos aceitos: `.docx`, `.txt`, `.mp3`, `.mp4` apenas (`app/core/constants.py::ALLOWED_EXTENSIONS`,
espelhando `gera_d_engine.ingestion.loader`). `.wav`/`.m4a` retornam 4xx claro, nunca 500.

### Metodologia/calibração vem do Postgres (Fase 7)

A calibração **não** vem mais de `engine/src/gera_d_engine/calibration/v1.yaml`.
`engine_integration/calibration_builder.py` monta o objeto `Calibration` a partir das tabelas
`methodologies` / `methodology_categories` / `calibrators`, e `EngineAdapter.from_published(db)`
resolve a versão `PUBLISHED` a cada análise (não é singleton de boot). Nunca reintroduza
`gera_d_engine.calibration.load_calibration()` no caminho do backend — isso reverte a migração
silenciosamente para o YAML com `lru_cache`.

Ciclo de vida: DRAFT → PUBLISHED → ARCHIVED, com índice parcial único garantindo no máximo 1
`PUBLISHED`. `MethodologyService.publish()` valida que as categorias casam exatamente com
`CriterionKey` e que há 4 calibradores cobrindo as 4 cores do farol (senão 409).
`analyses.methodology_version_id` registra qual versão gerou cada resultado.

### Custo de IA (FinAI, Fase 8)

`backend/app/ai_cost/` captura o consumo de OpenAI **sem tocar a engine**. Pacote próprio (não
`engine_integration/`) porque dois dos quatro pontos de consumo — assistente e
`scripts/ingest_methodology.py` — não têm nada a ver com `gera_d_engine`; nenhum arquivo de
`ai_cost/` importa a engine.

O mecanismo é o hook de ContextVar do LangChain: `register_configure_hook` em
`ai_cost/callback.py` faz qualquer `invoke()` de chat model dentro do escopo de
`track_ai_usage(...)` cair num `BaseCallbackHandler` nosso — inclusive as 6-7 chamadas feitas
lá dentro da engine. **`register_configure_hook` faz `append` numa lista global sem dedup**:
o registro é único, no import do módulo, e por job só se faz `set()`/`reset()` do ContextVar.
Nunca substituir por `get_usage_metadata_callback()` do langchain (vaza uma entrada por job e
perde granularidade por chamada) — há teste de regressão em
`tests/unit/test_ai_cost_callback.py`.

A etapa de cada chamada vem do nome da classe pydantic de `with_structured_output`
(`invocation_params["response_format"]`), mapeado em `ai_cost/stages.py` e travado por
`tests/contract/test_ai_cost_stage_map.py` — se a engine renomear um nó, esse teste quebra em
vez do painel degradar em silêncio.

Whisper não passa por LangChain (SDK bruto na engine): a duração vem de `ffprobe`
(`ai_cost/audio.py`) e o custo é por minuto. Embeddings não emitem callback: tokens contados
com `tiktoken` (`ai_cost/tokenization.py`, `tokens_estimated=True`).

Invariante: **contabilizar custo nunca falha uma análise nem uma resposta do assistente** —
sink em sessão própria, flush único no `finally`, try/except em tudo. Falha de preço ou de
medição vira `cost_status=NO_PRICE|NO_UNITS`, nunca exceção. `AI_COST_TRACKING_ENABLED=false`
desliga a captura inteira.

Custo é `Numeric(18, 10)` e **congelado** na gravação (escala menor zeraria embeddings; o
snapshot é o que mantém meses fechados imutáveis). Reprecificar histórico é explícito, via
`POST /ai-costs/prices/{id}/recalculate`.

### Autorização

JWT em cookie httpOnly (`app/core/security.py`), stateless. `get_current_user` lê o cookie e exige
`UserStatus.ACTIVE`; `require_role(UserRole.ADMIN)` protege escrita administrativa.

Padrão **dono-ou-ADMIN retorna 404, nunca 403** para recurso de outro usuário (não revelar
existência de IDs) — ver `routes/analyses.py::_get_owned_or_404`. O escopo de leitura (próprias vs.
globais) é sempre derivado do usuário autenticado, nunca de parâmetro do cliente.

`UserRole` tem três valores: `ADMIN`, `GESTOR`, `COLABORADOR`. `User.manager_id` liga um
COLABORADOR ao seu GESTOR (hierarquia de um nível só, sem encadeamento); `UserRepository.
list_subordinates` resolve a equipe, validada em `UserService`. `require_role(UserRole.GESTOR)`
protege rotas de equipe; `AnalysisService`/`DashboardService` têm ramos específicos para o GESTOR
(quadro de equipe).

Cada usuário tem cota diária de análises: `DAILY_ANALYSIS_LIMIT_PER_OWNER` (`app/core/config.py`,
hoje 4). `AnalysisService.get_daily_quota`/`create_and_store` verificam o uso do dia e levantam
`DailyAnalysisLimitError` quando excedida.

### Farol (classificação da nota)

`overall_band_label` dentro do JSONB `analysis_result` é a fonte de verdade. `app/core/farol.py`
só traduz label → cor (mapa lido do Postgres, cobrindo versões arquivadas) → nível de UI. Backend e
frontend **nunca** recalculam a faixa a partir de `overall_score`: a nota geral vem de julgamento
holístico da IA, não de fórmula.

## Arquitetura do frontend

```
api/client.ts      fetch wrappers (sempre `credentials: "include"` pelo cookie de auth) + ApiError
api/<recurso>.ts   uma função por endpoint
types/<recurso>.ts espelho manual dos schemas pydantic
hooks/use*.ts      um hook por operação, @tanstack/react-query (queryKey estável, invalidação no mutate)
routes/*.tsx       uma página por rota, cada uma com seu `.test.tsx` ao lado
components/        ui/ (primitivos) · forms/ · results/ · auth/ · library/ · processing/ · aicost/
styles/tokens/     design tokens em CSS vars (cores, tipografia, spacing, elevação)
```

Rotas em `App.tsx`: tudo dentro de `<ProtectedRoute>` + `AuthenticatedShell` (sidebar); telas
administrativas (`/admin`, `/calibracao`, `/usuarios`, `/custos-ia`) adicionalmente envolvidas por
`<RequireRole allow={["ADMIN"]}>` dentro do próprio `AuthenticatedShell`.

Fluxo para expor um endpoint novo na UI: `api/` → `types/` → `hooks/` → página, nessa ordem.
Testes de página usam Testing Library + mock do módulo de `api/`, nunca navegador real.
