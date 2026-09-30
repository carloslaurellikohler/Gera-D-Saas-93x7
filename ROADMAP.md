# Roadmap GerAD — de engine isolada a SaaS completo

Este documento consolida o plano de evolução do GerAD para que não seja necessário
reconstruir esse contexto a cada conversa. Ele é atualizado conforme as fases avançam.

## Visão do produto

O GerAD é uma plataforma de avaliação de qualidade em atendimento comercial. Analisa, via
IA generativa, conversas entre um **CS** (consultor da Franq, empresa parceira) e um **PB**
(Personal Banker, o profissional avaliado), aplicando a metodologia proprietária **93x7®**.

Fluxo central: upload de transcrição (`.docx`/`.txt`) ou áudio/vídeo (`.mp3`/`.mp4`) →
transcrição (quando necessário) → análise via IA em várias etapas → dois relatórios em PDF
(Executivo e Detalhado) + resultados na plataforma, com acompanhamento assíncrono do
processamento.

A metodologia avalia 6 critérios comportamentais (Posicionamento, Conexão, Sondagem,
Direcionamento, Encaminhamento, Eficiência da Condução), consolidados em **Pilar 93**
(comportamento/condução) e **Pilar 7** (conteúdo/resultado). Cada análise recebe uma nota
geral classificada em 4 faixas de farol: **Excelente** (verde) · **Atenção** (amarelo) ·
**Desenvolvimento Prioritário** (laranja) · **Desenvolvimento Crítico** (vermelho).

Fonte de verdade da metodologia: `docs/metodologia_93x7.pdf`.

## Arquitetura (não muda entre fases, salvo indicação contrária)

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

- `engine/` — motor de análise (`gera_d_engine`), pacote Python **isolado e intocado** por
  qualquer trabalho de backend/frontend. Pipeline de 9 etapas (ingestão → normalização →
  extração factual → contexto PB → análise comportamental → análise de consequência →
  desenvolvimento → T&D → renderização), calibrado por `engine/src/gera_d_engine/calibration/v1.yaml`.
  Roda hoje via CLI (`python -m gera_d_engine.cli analyze ...`); ver `engine/README.md`.
- `backend/` — API FastAPI + orquestração + persistência + worker assíncrono, construídos
  ao redor da engine. Só `engine_integration/` importa `gera_d_engine`; contrato garantido
  por `backend/tests/contract/test_engine_contract.py`.
- `frontend/` — SPA React 19 + TypeScript + Vite + react-router-dom 7 + @tanstack/react-query 5.

Formatos de entrada suportados hoje: **`.docx`, `.txt`, `.mp3`, `.mp4`** apenas (`.wav`/`.m4a`
não são aceitos — limitação da engine, comunicada como erro 4xx claro, nunca 500).

## Estado atual (o que já existe)

- **Motor 93x7®** — funcional, pipeline completo de 9 etapas, gera `AnalysisResult` +
  PDFs Executivo/Detalhado via WeasyPrint.
- **Backend/Frontend/Docker Compose ao redor da engine** — API REST (`/api/v1/analyses`),
  worker Celery + Redis, Postgres, 5 serviços via Docker Compose. Telas: Dashboard, Nova
  Análise, Processamento, Resultado (abas Resumo/Análise/Relatório/Transcrição).
- **Fase 1 — Fundação de autenticação** — JWT em cookie httpOnly, tabela `users`
  (`role`: ADMIN/USER, `status`: ACTIVE/INACTIVE), rotas `/auth/login`, `/auth/logout`,
  `/auth/me`, shell autenticado (sidebar + menu de usuário), `ProtectedRoute` no frontend,
  script `backend/scripts/seed_admin.py` para bootstrap do primeiro admin. Sem
  autocadastro público.
- **Fase 3 — Integração de `Analysis` com usuários autenticados** — `user_id` (FK
  nullable para `users`, `ondelete=SET NULL`) em `analyses`; `AnalysisService` usa o
  usuário autenticado (`current_user.id`/`.name`) em vez de
  `DEFAULT_CS_ID`/`DEFAULT_CS_NAME` na criação; rotas `/analyses/*` agora exigem
  `Depends(get_current_user)`; leitura/exclusão seguem a regra dono-ou-ADMIN (404 para
  quem não é dono nem ADMIN, nunca 403 — evita revelar a existência do ID); listagem
  filtrada por `user_id` para usuário comum, sem filtro para ADMIN. Análises criadas
  antes desta fase ficam com `user_id NULL` (sem backfill artificial).
- **Fase 2 — Dashboard do usuário + administrativo** — endpoint `GET /dashboard/stats`
  (`DashboardService`/`DashboardRepository`, só leitura), com volume por status,
  distribuição por farol (normalizada de `analysis_result->>'overall_band_label'` via
  `app/core/farol.py`, nunca recalculada a partir do `overall_score`), tendência semanal
  de nota média, e um "quadro individual" só para ADMIN — agrupado por **PB avaliado**
  (`pb_id`/`participant_name`), não pelo usuário/CS dono do registro. Escopo (próprias
  análises vs. globais) sempre derivado do usuário autenticado, nunca de parâmetro do
  cliente. `AdminDashboardPage` e a seção de KPIs de `DashboardPage` conectadas a esse
  endpoint; gráfico de tendência com `recharts` (nova dependência do frontend).

## Roadmap das fases seguintes

Cada fase deve começar com uma nova rodada de exploração + planejamento antes de ser
implementada — os itens abaixo são a visão de alto nível, não um plano de implementação
pronto.

- **Fase 4 — Evolução de métricas**: gráficos temporais e por categoria (ex.: radar dos 6
  critérios), baseados nos dados já persistidos em `analysis_result` (JSONB).
- **Fase 5 — Biblioteca de conteúdo + trilhas de treinamento**: novas tabelas `Content`,
  `LearningPath`, upload de materiais, conectando com os pontos de desenvolvimento e
  recomendações de T&D dos relatórios.
- **Fase 6 — Assistente de IA (chatbot RAG)**: reaproveita o padrão `ChatOpenAI` do engine,
  mas como módulo novo e paralelo — hoje não existe infraestrutura de RAG/vector store no
  projeto, será construída do zero.
- **Fase 7 — Migração da calibração para Postgres**: tabelas versionadas (`Methodology`,
  `MethodologyCategory`, `Calibrator`) substituindo `calibration/v1.yaml`, com estados
  DRAFT/PUBLISHED/ARCHIVED e versionamento por análise (nunca recalcular resultados antigos
  silenciosamente). Mudança sensível — exige plano próprio dado o vínculo com os testes de
  contrato da engine.
- **Fase 8 — Hardening**: segurança, testes, performance, auditoria administrativa.

## Identidade visual e mockups

Foi produzido um prompt detalhado para o Claude Design cobrindo:
- As 6 telas já implementadas (Login, Dashboard, Nova Análise, Processamento, Resultado,
  Shell autenticado).
- As 6 telas do roadmap futuro (Dashboard administrativo, Métricas/Evolução, Biblioteca +
  Trilhas, Assistente de IA, Administração de Metodologia/Calibração, Administração de
  Usuários).
- Paleta atual (`frontend/src/App.css`) como ponto de partida, não como restrição — cores
  de farol das 4 faixas precisam manter contraste acessível (AA) e distinção visual clara
  em relação aos badges de status de processamento.
- Tom: corporativo, analítico, confiável — ferramenta de trabalho para avaliação e
  desenvolvimento de profissionais em contexto bancário/financeiro, não produto consumer.

## Notas de decisão que não devem ser reabertas sem motivo

- A engine (`engine/`) nunca é modificada por trabalho de backend/frontend.
- Auth é stateless (JWT em cookie httpOnly), não sessão via Redis.
- Sem autocadastro público — usuários são criados por admin (ou seed script).
- `.wav`/`.m4a` não são suportados; não introduzir transcodificação (ffmpeg) para contornar
  isso sem sinalizar antes ao usuário.
- Testes de repositório usam Postgres descartável, nunca SQLite.
- Nota geral de uma análise vem do julgamento holístico das etapas de IA, nunca de uma
  fórmula aritmética simples sobre os pilares.
