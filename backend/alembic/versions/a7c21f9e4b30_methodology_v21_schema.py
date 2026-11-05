"""metodologia v2.1: racional estruturado e nota ponderada

Schema da Fase 9. O racional que a IA aplica para chegar à nota deixa de ser prosa solta
em MethodologyCategory.description e passa a ser dado estruturado e versionado: âncoras
observáveis 0-10, exemplos ancorados, rubrica de subdimensões 0-4 e regras de
elegibilidade de faixa. O seed do conteúdo em si vem na migration seguinte.

Revision ID: a7c21f9e4b30
Revises: 8fedcfaf1406
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a7c21f9e4b30"
down_revision = "8fedcfaf1406"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- definição refinada do critério (Manual V2.1, seção 4) --------------------
    for column in (
        sa.Column("central_question", sa.Text(), nullable=True),
        sa.Column("what_it_is_not", sa.Text(), nullable=True),
        sa.Column("positive_evidence", sa.Text(), nullable=True),
        sa.Column("negative_evidence", sa.Text(), nullable=True),
        sa.Column("cross_impact_text", sa.Text(), nullable=True),
    ):
        op.add_column("methodology_categories", column)

    # server_default="0": as versões já existentes não têm pesos, e o publish só exige
    # soma 1 daqui em diante — uma versão arquivada continua válida como registro.
    op.add_column(
        "methodology_categories",
        sa.Column("weight", sa.Numeric(5, 4), nullable=False, server_default="0"),
    )

    # --- âncoras: a régua observável 0-10 ----------------------------------------
    op.create_table(
        "methodology_anchors",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("methodology_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "scope",
            sa.Enum("CRITERION", "PILLAR", name="anchor_scope", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("scope_key", sa.String(32), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("descriptor", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["methodology_id"],
            ["methodologies.id"],
            name="fk_methodology_anchors_methodology_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "methodology_id", "scope", "scope_key", "level", name="uq_methodology_anchor_level"
        ),
    )
    op.create_index("ix_methodology_anchors_methodology_id", "methodology_anchors", ["methodology_id"])

    # --- exemplos ancorados: o material few-shot do prompt ------------------------
    op.create_table(
        "methodology_anchor_examples",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("methodology_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("criterion_key", sa.String(32), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("scenario", sa.Text(), nullable=True),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["methodology_id"],
            ["methodologies.id"],
            name="fk_methodology_anchor_examples_methodology_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_methodology_anchor_examples_methodology_id", "methodology_anchor_examples", ["methodology_id"]
    )

    # --- subdimensões: rubrica de auditoria 0-4 ----------------------------------
    op.create_table(
        "methodology_subdimensions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("methodology_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("criterion_key", sa.String(32), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("levels", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["methodology_id"],
            ["methodologies.id"],
            name="fk_methodology_subdimensions_methodology_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_methodology_subdimensions_methodology_id", "methodology_subdimensions", ["methodology_id"]
    )

    # --- elegibilidade de faixa: os tetos que impedem notas ----------------------
    op.create_table(
        "methodology_eligibility_rules",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("methodology_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_key", sa.String(32), nullable=False),
        sa.Column("condition", sa.Text(), nullable=False),
        sa.Column(
            "effect",
            sa.Enum("CAP", "NOTE", name="eligibility_effect", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("max_score", sa.Float(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["methodology_id"],
            ["methodologies.id"],
            name="fk_methodology_eligibility_rules_methodology_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_methodology_eligibility_rules_methodology_id",
        "methodology_eligibility_rules",
        ["methodology_id"],
    )

    # --- auditoria da nota holística (pré-ponderação) ----------------------------
    op.add_column("analyses", sa.Column("holistic_overall_score", sa.Float(), nullable=True))
    op.add_column("analyses", sa.Column("holistic_overall_band_label", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "holistic_overall_band_label")
    op.drop_column("analyses", "holistic_overall_score")

    op.drop_index("ix_methodology_eligibility_rules_methodology_id", table_name="methodology_eligibility_rules")
    op.drop_table("methodology_eligibility_rules")
    op.drop_index("ix_methodology_subdimensions_methodology_id", table_name="methodology_subdimensions")
    op.drop_table("methodology_subdimensions")
    op.drop_index("ix_methodology_anchor_examples_methodology_id", table_name="methodology_anchor_examples")
    op.drop_table("methodology_anchor_examples")
    op.drop_index("ix_methodology_anchors_methodology_id", table_name="methodology_anchors")
    op.drop_table("methodology_anchors")

    for column in (
        "weight",
        "cross_impact_text",
        "negative_evidence",
        "positive_evidence",
        "what_it_is_not",
        "central_question",
    ):
        op.drop_column("methodology_categories", column)
