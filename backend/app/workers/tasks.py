from __future__ import annotations

import logging
import uuid

from openai import APIConnectionError, APITimeoutError, RateLimitError

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.engine_integration.adapter import EngineAdapter
from app.repositories.analysis_repository import AnalysisRepository
from app.services.analysis_service import AnalysisService
from app.storage.local_storage import LocalDiskStorage
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)

# Só erros transitórios da OpenAI valem retry — falhas determinísticas (arquivo inválido,
# schema, WeasyPrint) vão direto para FAILED sem queimar créditos tentando de novo.
_TRANSIENT_ERRORS = (RateLimitError, APITimeoutError, APIConnectionError)


def _build_analysis_service(db) -> AnalysisService:
    settings = get_settings()
    return AnalysisService(
        repo=AnalysisRepository(db),
        storage=LocalDiskStorage(settings.STORAGE_DIR),
        engine=EngineAdapter.from_published(db),
        settings=settings,
    )


@celery_app.task(bind=True, max_retries=2, default_retry_delay=15, retry_backoff=True)
def process_analysis_task(self, analysis_id: str) -> None:
    db = SessionLocal()
    try:
        service = _build_analysis_service(db)
        service.run_analysis_job(uuid.UUID(analysis_id))
    except _TRANSIENT_ERRORS as exc:
        log.warning("transient engine error for analysis %s, retrying: %s", analysis_id, exc)
        raise self.retry(exc=exc)
    except Exception:
        # AnalysisService já persistiu FAILED + mensagem segura; não faz sentido re-tentar
        # um erro determinístico (arquivo inválido, schema, etc.) e queimar créditos de API.
        log.info("analysis %s ended in FAILED state, not retrying", analysis_id)
    finally:
        db.close()
