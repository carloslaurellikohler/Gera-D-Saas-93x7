from __future__ import annotations

from app.models.methodology_chunk import MethodologyChunk
from app.repositories.methodology_chunk_repository import MethodologyChunkRepository


def test_replace_all_then_list_all_in_chunk_order(db_session):
    repo = MethodologyChunkRepository(db_session)
    repo.replace_all(
        [
            MethodologyChunk(chunk_index=1, content="segundo", embedding=[0.1, 0.2]),
            MethodologyChunk(chunk_index=0, content="primeiro", embedding=[0.3, 0.4]),
        ]
    )

    chunks = repo.list_all()

    assert [c.content for c in chunks] == ["primeiro", "segundo"]


def test_replace_all_discards_previous_corpus(db_session):
    repo = MethodologyChunkRepository(db_session)
    repo.replace_all([MethodologyChunk(chunk_index=0, content="velho", embedding=[0.1])])

    repo.replace_all([MethodologyChunk(chunk_index=0, content="novo", embedding=[0.2])])

    chunks = repo.list_all()
    assert [c.content for c in chunks] == ["novo"]
