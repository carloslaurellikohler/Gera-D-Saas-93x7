"""create ai cost tables

Revision ID: e7a2c9f4b1d8
Revises: c3f5e9a72d64
Create Date: 2026-10-08 12:10:00.000000

Tabelas do FinAI (observabilidade de custo de IA). Três decisões que valem registro:

- cost_usd é Numeric(18, 10), não Float nem escala menor. 10 tokens de embedding a
  US$ 0,02/milhão custam US$ 0,0000002 — com escala 6 isso arredonda para zero e o custo de
  embedding desapareceria da soma. SUM() sobre numeric no Postgres é exato.
- analysis_id/user_id usam SET NULL, nunca CASCADE: existe DELETE /analyses/{id}, e com
  cascade apagar uma análise apagaria gasto já incorrido, mudando o total do mês
  retroativamente. Custo é histórico financeiro — permanece.
- ai_model_prices tem só valid_from, sem valid_to: com os dois campos existiria a
  possibilidade de buracos e sobreposições inconsistentes.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a2c9f4b1d8'
down_revision: Union[str, Sequence[str], None] = 'c3f5e9a72d64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ai_model_prices vem primeiro: ai_usage_events referencia essa tabela.
    op.create_table(
        'ai_model_prices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('model', sa.String(length=64), nullable=False),
        sa.Column(
            'operation',
            sa.Enum('CHAT', 'TRANSCRIPTION', 'EMBEDDING', name='ai_usage_operation', native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column('valid_from', sa.Date(), nullable=False),
        # Preços de token são por 1 milhão de tokens — é como a OpenAI publica, então o
        # ADMIN digita o número direto da página de preços. Nullable porque cada operação
        # usa um subconjunto: chat usa as três de token, embedding só a de input,
        # transcrição só usd_per_minute.
        sa.Column('input_usd_per_mtok', sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column('cached_input_usd_per_mtok', sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column('output_usd_per_mtok', sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column('usd_per_minute', sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column('is_placeholder', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model', 'operation', 'valid_from', name='uq_ai_model_price_vigencia'),
        sa.ForeignKeyConstraint(
            ['updated_by_id'], ['users.id'], name='fk_ai_model_prices_updated_by_id_users', ondelete='SET NULL'
        ),
    )
    op.create_index(op.f('ix_ai_model_prices_updated_by_id'), 'ai_model_prices', ['updated_by_id'], unique=False)
    op.create_index(
        'ix_ai_model_prices_model_operation_valid_from',
        'ai_model_prices',
        ['model', 'operation', 'valid_from'],
        unique=False,
    )

    op.create_table(
        'ai_usage_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column(
            'feature',
            sa.Enum('ANALYSIS', 'ASSISTANT', 'INGESTION', name='ai_usage_feature', native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column(
            'operation',
            sa.Enum('CHAT', 'TRANSCRIPTION', 'EMBEDDING', name='ai_usage_operation', native_enum=False, length=16),
            nullable=False,
        ),
        # Derivada do nome da classe pydantic de with_structured_output (ver
        # app/ai_cost/stages.py) — determinística por chamada. Nullable porque um esquema
        # desconhecido é possível se a engine mudar.
        sa.Column('stage', sa.String(length=48), nullable=True),
        sa.Column('model', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('analysis_id', sa.UUID(), nullable=True),
        # Agrupa as chamadas de UMA tentativa de job, distinguindo as tentativas de uma
        # mesma análise.
        sa.Column('job_run_id', sa.UUID(), nullable=True),
        # Tentativa do Celery (0 = primeira). Torna visível o custo de retry, que hoje
        # reexecuta o pipeline inteiro sem deixar rastro.
        sa.Column('attempt', sa.SmallInteger(), nullable=False, server_default=sa.text('0')),
        # Quantas chamadas à API a linha representa — >1 só no Whisper chunkado.
        sa.Column('calls', sa.SmallInteger(), nullable=False, server_default=sa.text('1')),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default=sa.text('0')),
        # Subconjunto de input_tokens; o input faturado cheio é input - cached_input.
        sa.Column('cached_input_tokens', sa.Integer(), nullable=False, server_default=sa.text('0')),
        # Subconjunto de output_tokens — breakdown informativo, NUNCA somado ao custo
        # (output_tokens já os inclui; somar seria cobrar em dobro).
        sa.Column('reasoning_tokens', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('audio_seconds', sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column('tokens_estimated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        # Escala 10 é requisito, não exagero — ver docstring do módulo. Snapshot congelado
        # na gravação, para que mudança de preço não reescreva meses fechados.
        sa.Column('cost_usd', sa.Numeric(precision=18, scale=10), nullable=False, server_default=sa.text('0')),
        sa.Column(
            'cost_status',
            sa.Enum('PRICED', 'NO_PRICE', 'NO_UNITS', name='ai_usage_cost_status', native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column('price_id', sa.UUID(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('error_type', sa.String(length=120), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        # SET NULL em user_id/analysis_id: o gasto aconteceu de fato e precisa continuar
        # somando no total do período mesmo que o usuário ou a análise sejam removidos.
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'], name='fk_ai_usage_events_user_id_users', ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['analysis_id'], ['analyses.id'], name='fk_ai_usage_events_analysis_id_analyses', ondelete='SET NULL'
        ),
        # SET NULL: o custo já está congelado na linha, então perder o ponteiro de auditoria
        # é degradação aceitável.
        sa.ForeignKeyConstraint(
            ['price_id'],
            ['ai_model_prices.id'],
            name='fk_ai_usage_events_price_id_ai_model_prices',
            ondelete='SET NULL',
        ),
    )
    op.create_index(op.f('ix_ai_usage_events_occurred_at'), 'ai_usage_events', ['occurred_at'], unique=False)
    op.create_index(op.f('ix_ai_usage_events_feature'), 'ai_usage_events', ['feature'], unique=False)
    op.create_index(op.f('ix_ai_usage_events_user_id'), 'ai_usage_events', ['user_id'], unique=False)
    op.create_index(op.f('ix_ai_usage_events_analysis_id'), 'ai_usage_events', ['analysis_id'], unique=False)
    op.create_index(op.f('ix_ai_usage_events_job_run_id'), 'ai_usage_events', ['job_run_id'], unique=False)
    op.create_index(op.f('ix_ai_usage_events_price_id'), 'ai_usage_events', ['price_id'], unique=False)
    # Predicado de praticamente toda agregação da tela (janela de período + corte por origem).
    op.create_index(
        'ix_ai_usage_events_occurred_at_feature', 'ai_usage_events', ['occurred_at', 'feature'], unique=False
    )

    op.create_table(
        'ai_cost_budgets',
        sa.Column('id', sa.UUID(), nullable=False),
        # Sempre o dia 1 do mês (normalizado no service). Versionado por mês pelo mesmo
        # motivo que o preço é versionado por vigência: "estourei a meta de setembro?"
        # exige a meta de setembro, e uma linha única reescreveria meses já fechados.
        sa.Column('month', sa.Date(), nullable=False),
        sa.Column('amount_usd', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('month', name='uq_ai_cost_budget_month'),
        sa.ForeignKeyConstraint(
            ['updated_by_id'], ['users.id'], name='fk_ai_cost_budgets_updated_by_id_users', ondelete='SET NULL'
        ),
    )
    op.create_index(op.f('ix_ai_cost_budgets_updated_by_id'), 'ai_cost_budgets', ['updated_by_id'], unique=False)

    op.create_table(
        'ai_cost_settings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('warn_threshold_pct', sa.Integer(), nullable=False, server_default=sa.text('80')),
        # Taxa manual, só para exibição. Nenhum valor em BRL é persistido — a taxa muda, e
        # um valor em reais gravado hoje seria mentira amanhã.
        sa.Column('usd_to_brl_rate', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('usd_to_brl_rate_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['updated_by_id'], ['users.id'], name='fk_ai_cost_settings_updated_by_id_users', ondelete='SET NULL'
        ),
    )
    op.create_index(op.f('ix_ai_cost_settings_updated_by_id'), 'ai_cost_settings', ['updated_by_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_ai_cost_settings_updated_by_id'), table_name='ai_cost_settings')
    op.drop_table('ai_cost_settings')
    op.drop_index(op.f('ix_ai_cost_budgets_updated_by_id'), table_name='ai_cost_budgets')
    op.drop_table('ai_cost_budgets')
    op.drop_index('ix_ai_usage_events_occurred_at_feature', table_name='ai_usage_events')
    op.drop_index(op.f('ix_ai_usage_events_price_id'), table_name='ai_usage_events')
    op.drop_index(op.f('ix_ai_usage_events_job_run_id'), table_name='ai_usage_events')
    op.drop_index(op.f('ix_ai_usage_events_analysis_id'), table_name='ai_usage_events')
    op.drop_index(op.f('ix_ai_usage_events_user_id'), table_name='ai_usage_events')
    op.drop_index(op.f('ix_ai_usage_events_feature'), table_name='ai_usage_events')
    op.drop_index(op.f('ix_ai_usage_events_occurred_at'), table_name='ai_usage_events')
    op.drop_table('ai_usage_events')
    op.drop_index('ix_ai_model_prices_model_operation_valid_from', table_name='ai_model_prices')
    op.drop_index(op.f('ix_ai_model_prices_updated_by_id'), table_name='ai_model_prices')
    op.drop_table('ai_model_prices')
