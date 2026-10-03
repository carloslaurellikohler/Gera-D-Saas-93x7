"""seed initial methodology from v1.yaml

Revision ID: 5b77efb26e8d
Revises: bcce5fc7b439
Create Date: 2026-10-03 00:10:00.000000

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5b77efb26e8d'
down_revision: Union[str, Sequence[str], None] = 'bcce5fc7b439'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tudo de `raw` que não vira coluna própria de Methodology cai no JSONB `content`
# (prosa global nunca filtrada em SQL — ver app/models/methodology.py).
_NON_CONTENT_KEYS = {"calibration_version", "methodology_name", "project", "criteria", "score_bands"}
_CATEGORY_EXTRA_KEYS = (
    "good_performance", "risks", "calibration_note", "critical_rule", "cross_impact", "desired_structure",
)

# Fixo (gerado uma vez) para que o downgrade saiba exatamente o que remover.
_METHODOLOGY_ID = uuid.UUID("a1f3c9d2-6e4b-4a1e-9c3d-1f2e3a4b5c6d")

methodologies = sa.table(
    "methodologies",
    sa.column("id", sa.UUID()),
    sa.column("calibration_version", sa.String()),
    sa.column("methodology_name", sa.String()),
    sa.column("project", sa.String()),
    sa.column("status", sa.String()),
    sa.column("content", postgresql.JSONB()),
    sa.column("published_at", sa.DateTime(timezone=True)),
    sa.column("created_at", sa.DateTime(timezone=True)),
)
methodology_categories = sa.table(
    "methodology_categories",
    sa.column("id", sa.UUID()),
    sa.column("methodology_id", sa.UUID()),
    sa.column("key", sa.String()),
    sa.column("label", sa.String()),
    sa.column("description", sa.Text()),
    sa.column("order_index", sa.Integer()),
    sa.column("extra", postgresql.JSONB()),
)
calibrators = sa.table(
    "calibrators",
    sa.column("id", sa.UUID()),
    sa.column("methodology_id", sa.UUID()),
    sa.column("key", sa.String()),
    sa.column("label", sa.String()),
    sa.column("color", sa.String()),
    sa.column("min", sa.Float()),
    sa.column("max", sa.Float()),
    sa.column("order_index", sa.Integer()),
)


def upgrade() -> None:
    """Upgrade schema."""
    # `get_analysis_service`/o worker Celery (Fase 7) exigem sempre existir uma
    # Methodology PUBLISHED — sem isso, análises novas falham com 503. Esta migration
    # precisa deixar o sistema operacional sozinha, por isso é seed de dados, não um
    # script manual como scripts/ingest_methodology.py.
    #
    # Importa a engine só aqui (migration de dados única, não um caminho de código
    # recorrente de app/ — o teste de contrato só guarda app/engine_integration/). A
    # engine já está instalada no container (ver Dockerfile: `pip install -e /engine`)
    # e ler o YAML real via load_calibration() garante fidelidade byte-a-byte com
    # v1.yaml sem o risco de uma transcrição manual divergir.
    from gera_d_engine.calibration import load_calibration

    raw = load_calibration().raw
    now = datetime.now(timezone.utc)

    content = {key: value for key, value in raw.items() if key not in _NON_CONTENT_KEYS}

    op.bulk_insert(methodologies, [{
        "id": _METHODOLOGY_ID,
        "calibration_version": raw["calibration_version"],
        "methodology_name": raw["methodology_name"],
        "project": raw["project"],
        "status": "PUBLISHED",
        "content": content,
        "published_at": now,
        "created_at": now,
    }])

    category_rows = []
    for order_index, (key, crit) in enumerate(raw["criteria"].items()):
        extra = {extra_key: crit[extra_key] for extra_key in _CATEGORY_EXTRA_KEYS if extra_key in crit}
        category_rows.append({
            "id": uuid.uuid4(),
            "methodology_id": _METHODOLOGY_ID,
            "key": key,
            "label": crit["label"],
            "description": crit["description"],
            "order_index": order_index,
            "extra": extra,
        })
    op.bulk_insert(methodology_categories, category_rows)

    calibrator_rows = [
        {
            "id": uuid.uuid4(),
            "methodology_id": _METHODOLOGY_ID,
            "key": band["key"],
            "label": band["label"],
            "color": band["color"],
            "min": float(band["min"]),
            "max": float(band["max"]),
            "order_index": order_index,
        }
        for order_index, band in enumerate(raw["score_bands"])
    ]
    op.bulk_insert(calibrators, calibrator_rows)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.delete(calibrators).where(calibrators.c.methodology_id == _METHODOLOGY_ID))
    op.execute(sa.delete(methodology_categories).where(methodology_categories.c.methodology_id == _METHODOLOGY_ID))
    op.execute(sa.delete(methodologies).where(methodologies.c.id == _METHODOLOGY_ID))
