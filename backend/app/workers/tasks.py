from __future__ import annotations

import logging
import uuid

from openai import APIConnectionError, APITimeoutError, RateLimitError

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.engine_integration.adapter import EngineAdapter
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.runtime_settings_repository import RuntimeSettingsRepository
from app.services.analysis_service import AnalysisService
from app.services.runtime_settings_service import build_effective_settings
from app.storage.local_storage import LocalDiskStorage
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)

# Só erros transitórios da OpenAI valem retry — falhas determinísticas (arquivo inválido,
# schema, WeasyPrint) vão direto para FAILED sem queimar créditos tentando de novo.
_TRANSIENT_ERRORS = (RateLimitError, APITimeoutError, APIConnectionError)


def _build_analysis_service(db) -> AnalysisService:
    # O worker é quem roda a análise, então ele também precisa ler os limites e o modelo do
    # banco — depender do ambiente do container reverteria a configuração em silêncio (o
    # compose nem repassa todas as vars para este serviço). A Session já está em mãos, então
    # não há conexão extra. EngineAdapter.from_published faz a própria leitura da mesma linha.
    settings = build_effective_settings(get_settings(), RuntimeSettingsRepository(db).get())
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
        # self.request.retries é 0 na primeira execução e 1/2 nas retentativas. Repassar
        # isso é o que faz o custo de retentativa aparecer na tela do FinAI: uma falha
        # transitória tardia reexecuta o pipeline inteiro e reemite todas as chamadas.
        service.run_analysis_job(uuid.UUID(analysis_id), attempt=self.request.retries or 0)
    except _TRANSIENT_ERRORS as exc:
        log.warning("transient engine error for analysis %s, retrying: %s", analysis_id, exc)
        raise self.retry(exc=exc)
    except Exception:
        # AnalysisService já persistiu FAILED + mensagem segura; não faz sentido re-tentar
        # um erro determinístico (arquivo inválido, schema, etc.) e queimar créditos de API.
        log.info("analysis %s ended in FAILED state, not retrying", analysis_id)
    finally:
        db.close()
