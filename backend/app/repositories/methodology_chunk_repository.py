"""Camada de acesso a dados dos chunks da metodologia 93x7® (Fase 6). Escrita só é usada
pelo script de ingestão (scripts/ingest_methodology.py) — nunca por uma rota HTTP."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.methodology_chunk import MethodologyChunk


class MethodologyChunkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[MethodologyChunk]:
        stmt = select(MethodologyChunk).order_by(MethodologyChunk.chunk_index)
        return list(self.db.execute(stmt).scalars().all())

    def replace_all(self, chunks: list[MethodologyChunk]) -> None:
        """Substitui o corpus inteiro — reprocessamento completo sempre que o PDF muda,
        nunca diff incremental (corpus pequeno, não compensa a complexidade)."""
        self.db.execute(delete(MethodologyChunk))
        self.db.add_all(chunks)
        self.db.commit()
