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

## Docker Compose (desenvolvimento)

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

## Deploy em produção

`docker-compose.prod.yml` é um arquivo **completo e independente**, não um override do
`docker-compose.yml`. As diferenças são estruturais — nginx no lugar do dev server do Vite,
nenhuma porta de aplicação publicada no host, variáveis obrigatórias em vez de defaults de
dev — e um override parcial deixaria o `ports: 8000:8000` do arquivo de desenvolvimento
valendo em produção.

Serviços: `postgres`, `redis`, `backend`, `worker`, `nginx`, `certbot`.

### Primeira subida

Pré-requisitos na VPS: Docker + Compose, DNS do domínio já apontando para o IP da máquina e
portas 80/443 liberadas no firewall (o desafio HTTP-01 do Let's Encrypt precisa da 80).

```bash
git clone <repo> && cd gera-d-saas-93x7

cp .env.production .env        # template de produção; preencha LETSENCRYPT_EMAIL
nano .env

./deploy/init-letsencrypt.sh   # emite o certificado inicial (uma vez)

export COMPOSE_FILE=docker-compose.prod.yml   # evita esquecer o -f em cada comando
docker compose up -d --build

docker compose exec backend python -m scripts.seed_admin          # 1º ADMIN
docker compose exec backend python -m scripts.ingest_methodology  # corpus RAG do assistente
```

`./deploy/init-letsencrypt.sh` aceita `STAGING=1` para ensaiar o fluxo contra o ambiente de
teste do Let's Encrypt: o certificado sai inválido no navegador, mas não consome o limite de
5 emissões por domínio por semana.

### nginx

É o único serviço exposto à internet, e acumula dois papéis: serve o SPA já compilado
(`frontend/Dockerfile.prod`, multi-stage Vite → nginx) e faz proxy de `/api/` e `/health`
para o `backend`. `backend`, `worker`, `postgres` e `redis` usam `expose`, não `ports` —
publicar a 8000 na VPS deixaria a API e o `/docs` acessíveis por IP, contornando o TLS.
`/docs` e `/openapi.json` caem no fallback do SPA de propósito, então a documentação da API
não fica pública.

Dois detalhes do `deploy/nginx/templates/gerad.conf.template` que não devem ser "limpados"
sem entender o motivo:

- **`${DOMAIN}` é substituído pelo envsubst do entrypoint da imagem oficial**, com
  `NGINX_ENVSUBST_FILTER: DOMAIN` restringindo a substituição a essa única variável. Sem o
  filtro, o envsubst comeria `$host`, `$uri` e `$request_uri` do próprio nginx. Por isso
  também **não existe `command:` no serviço `nginx`**: o `docker-entrypoint.sh` só roda o
  envsubst quando o primeiro argumento é literalmente `nginx`, e qualquer override pula a
  geração em silêncio — o nginx sobe sem server block algum, com `nginx -t` passando, porque
  config vazia é config válida.
- **O cache dos estáticos usa `expires`, não `add_header Cache-Control`.** Um `add_header`
  dentro de um `location` descarta todos os headers herdados do server block, o que apagaria
  o HSTS e os headers de segurança justamente no `index.html` e nos bundles.

### TLS

Emissão inicial manual (`deploy/init-letsencrypt.sh`), renovação automática: o serviço
`certbot` roda `certbot renew` de 12h em 12h e um hook em `/docker-entrypoint.d/` do nginx
recarrega a configuração de 6h em 6h — o certbot reescreve o certificado no volume
compartilhado sem avisar o nginx, que seguiria servindo o antigo da memória até expirar.

O script resolve um ovo-e-galinha: o server block `:443` referencia
`/etc/letsencrypt/live/$DOMAIN/fullchain.pem`, então o nginx não sobe sem certificado — mas
o certbot precisa do nginx no ar para responder ao desafio. Ele sobe com um autoassinado de
1 dia, pede o real e recarrega.

### Variáveis de produção

`.env.production` é o template (gitignorado junto com `.env` — contém segredos reais).
Diferenças que importam em relação ao `.env.example`:

- `DOMAIN` é a fonte única do domínio: alimenta `server_name`, o redirect e o caminho do
  certificado. `CORS_ORIGINS` e `VITE_API_BASE_URL` precisam acompanhar.
- `VITE_API_BASE_URL` aponta para o **mesmo domínio** do SPA (`https://<domínio>/api/v1`).
  É isso que torna as chamadas same-origin e permite `COOKIE_SAMESITE=lax`; um subdomínio
  separado para a API exigiria `SameSite=none`. Ele é **inlinado no bundle em tempo de
  build** (`import.meta.env`), então aparece em `build.args` e não em `environment:` —
  trocá-lo exige `docker compose up -d --build nginx`, não um restart.
- `COOKIE_SECURE=true`, obrigatório atrás de HTTPS.
- `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, `DATABASE_URL`, `OPENAI_API_KEY`, `CORS_ORIGINS`,
  `VITE_API_BASE_URL` e `DOMAIN` são declarados com `${VAR:?...}` no compose: um `.env`
  incompleto **aborta** em vez de subir silenciosamente com `dev-secret-change-me`.

### Operação

```bash
export COMPOSE_FILE=docker-compose.prod.yml

docker compose logs -f backend worker nginx
docker compose up -d --build backend worker   # após git pull (o fonte é copiado na imagem)
docker compose up -d --build nginx            # após mudar o frontend ou VITE_API_BASE_URL
docker compose restart nginx                  # após mudar o template do nginx (montado)
docker compose exec postgres pg_dump -U gerad gerad > backup.sql
```

Backup: os dados que não se recuperam de um rebuild estão nos volumes `pgdata` (banco) e
`storage_data` (uploads e PDFs gerados). `docker compose down -v` apaga os dois, mais o
`letsencrypt`.
