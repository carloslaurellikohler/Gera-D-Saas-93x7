"""Popula methodology_chunks a partir de docs/metodologia_93x7.pdf (Assistente de IA,
Fase 6) — a única fonte de conteúdo vetorizada, estática e pequena.

Rodar manualmente sempre que o PDF mudar (após `alembic upgrade head`):

    python -m scripts.ingest_methodology

Reprocessa o corpus inteiro a cada execução (DELETE + insert) — corpus pequeno, não
compensa a complexidade de um diff incremental. Nunca exposto via rota HTTP.
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from app.ai_cost import PendingUsage, count_tokens_batch, track_ai_usage
from app.ai_cost.stages import STAGE_CORPUS_EMBEDDING
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.ai_cost import AiUsageFeature, AiUsageOperation
from app.models.methodology_chunk import MethodologyChunk
from app.repositories.methodology_chunk_repository import MethodologyChunkRepository
from app.services.assistant_llm import build_embedding_model

_PDF_PATH = Path(__file__).resolve().parents[2] / "docs" / "metodologia_93x7.pdf"


def _extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    """Agrega parágrafos até ~chunk_size caracteres, com overlap entre chunks
    consecutivos — evita cortar frases no meio, mantendo chunks pequenos."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > chunk_size and current:
            chunks.append(current)
            overlap_tail = current[-overlap:] if overlap else ""
            current = f"{overlap_tail}\n\n{paragraph}" if overlap_tail else paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def main() -> None:
    settings = get_settings()

    if not _PDF_PATH.exists():
        print(f"{_PDF_PATH} não encontrado — nada a fazer.")
        return

    text = _extract_text(_PDF_PATH)
    chunks = _chunk_text(
        text, chunk_size=settings.ASSISTANT_CHUNK_SIZE, overlap=settings.ASSISTANT_CHUNK_OVERLAP
    )
    if not chunks:
        print("Nenhum texto extraído do PDF — nada a fazer.")
        return

    embedding_model = build_embedding_model(settings)
    # Reindexar o corpus é uma chamada de embedding em lote, e sem contabilizá-la o painel
    # de custo mentiria sempre que alguém rodasse este script. user_id fica nulo: é uma
    # execução de manutenção, não de um usuário da plataforma.
    with track_ai_usage(feature=AiUsageFeature.INGESTION) as usage:
        vectors = embedding_model.embed_documents(chunks)
        usage.add(
            PendingUsage(
                feature=AiUsageFeature.INGESTION,
                operation=AiUsageOperation.EMBEDDING,
                model=settings.ASSISTANT_EMBEDDING_MODEL,
                stage=STAGE_CORPUS_EMBEDDING,
                input_tokens=count_tokens_batch(
                    chunks, model=settings.ASSISTANT_EMBEDDING_MODEL
                )
                or 0,
                calls=1,
                tokens_estimated=True,
            )
        )

    db = SessionLocal()
    try:
        repo = MethodologyChunkRepository(db)
        repo.replace_all(
            [
                MethodologyChunk(chunk_index=i, content=chunk, embedding=vector, source_file=_PDF_PATH.name)
                for i, (chunk, vector) in enumerate(zip(chunks, vectors))
            ]
        )
    finally:
        db.close()

    print(f"{len(chunks)} chunks de '{_PDF_PATH.name}' indexados em methodology_chunks.")


if __name__ == "__main__":
    main()
