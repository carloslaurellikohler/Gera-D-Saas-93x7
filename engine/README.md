# Motor de Análise 93x7® — Gera D Consultoria

Motor de IA que recebe uma conversa entre CS e PB (texto já transcrito, áudio `.mp3` ou vídeo
`.mp4`) e gera duas avaliações estruturadas segundo a metodologia **93x7®**: Visão Executiva e
Visão Detalhada, em PDF e em JSON. Fonte de verdade da metodologia:
[`docs/metodologia_93x7.pdf`](../docs/metodologia_93x7.pdf).

## Setup

```bash
cd engine
python3 -m venv .venv
./.venv/bin/pip install -e ".[dev]"
cp .env.example .env   # preencha OPENAI_API_KEY
```

Variáveis de ambiente (`engine/.env`):

| Variável | Padrão | Descrição |
|---|---|---|
| `OPENAI_API_KEY` | — | obrigatória para rodar o pipeline (todas as etapas de IA) e o Whisper |
| `OPENAI_MODEL` | `gpt-4.1` | modelo usado em todas as etapas de IA |
| `OPENAI_TEMPERATURE` | `0.2` | temperatura padrão |

## Uso via CLI

```bash
./.venv/bin/python -m gera_d_engine.cli analyze \
    --input ../docs/exemplo1.docx \
    --cs-name "Alexandre Marques" \
    --pb-name "Francibele Ratzlaff" \
    --interaction-type "Onboarding / Boas-vindas" \
    --out-dir output
```

Também aceita `.txt`, `.mp3` e `.mp4` em `--input` (áudio/vídeo passam pela Whisper API — sem
diarização; veja a limitação abaixo). Gera:

- `output/interactions/<interaction_id>.json` — `AnalysisResult` completo (auditoria/integração futura)
- `output/reports/<cs>_<pb>_executivo_<id>.pdf`
- `output/reports/<cs>_<pb>_detalhado_<id>.pdf`

## Testes

```bash
./.venv/bin/python -m pytest tests/unit                 # sem custo de API
./.venv/bin/python -m pytest tests/integration -m slow   # roda a API de verdade (requer OPENAI_API_KEY)
```

## Limitação conhecida: diarização

A Whisper API não identifica quem fala. Para `.mp3`/`.mp4`, a etapa de normalização tenta inferir
a troca de falantes pelo conteúdo (usando os nomes de CS/PB informados), mas sem a confiabilidade
de uma diarização real. Para inputs já transcritos com falas identificadas (como
`docs/exemplo1.docx`), a atribuição de falante é determinística e confiável.

## Estrutura

Ver o plano de construção completo em
`~/.claude/plans/estou-montando-uma-aplica-o-nested-prism.md`, ou a árvore de módulos abaixo:

```
src/gera_d_engine/
  calibration/v1.yaml       # critérios, régua de notas, regras — fonte editável da calibragem
  ingestion/                # loaders: docx/txt e Whisper (mp3/mp4)
  pipeline/nodes/           # as 9 etapas da arquitetura (seção 21 da especificação)
  rendering/                # templates Jinja2 + export PDF via WeasyPrint
  storage/                  # persistência local (JSON por interação)
  cli.py
```

## Próximos passos sugeridos

- Validar a qualidade da análise rodando `analyze` sobre `docs/exemplo1.docx` com uma chave de API
  real e comparar com `docs/relatorio1_executivo.pdf` / `docs/relatorio1_detalhado.pdf`.
- Receber o arquivo de logo da Gera D para substituir o cabeçalho em texto nos templates.
- Calibragem v1.1+ conforme feedback de revisão humana (seção 27 da especificação).
