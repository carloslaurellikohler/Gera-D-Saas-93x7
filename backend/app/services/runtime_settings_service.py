"""Regra de negócio da configuração operacional editável em runtime (tela /configuracoes).

Dois papéis no mesmo módulo, de propósito:

- `build_effective_settings` é função pura, consumida por `api/deps.py` e por
  `workers/tasks.py`. É o **único** ponto onde o banco sobrepõe o `.env`.
- `RuntimeSettingsService` é consumido pela rota, e só por ela.

A separação importa porque o worker não tem request nem injeção de dependência: ele precisa da
função, não do service.
"""

from __future__ import annotations

from datetime import date

from app.core.config import Settings
from app.models.ai_cost import AiUsageOperation
from app.models.runtime_settings import RuntimeSettings
from app.models.user import User
from app.repositories.ai_price_repository import AiPriceRepository
from app.repositories.runtime_settings_repository import RuntimeSettingsRepository
from app.repositories.user_repository import UserRepository
from app.schemas.runtime_settings import RuntimeSettingsIn, RuntimeSettingsResponse
from app.services.assistant_llm import REASONING_MODEL_PREFIXES
from app.services.model_probe import probe_chat_model


def build_effective_settings(base: Settings, config: RuntimeSettings | None) -> Settings:
    """Settings do ambiente com os seis campos de runtime_settings sobrepostos.

    O banco sempre vence; `base` é bootstrap/fallback (vale quando a linha não existe: banco
    novo, migration de seed não aplicada, testes com create_all).

    Devolve um Settings NOVO — AnalysisService e AssistantService continuam lendo
    `self.settings.<CAMPO>` sem saber que a fonte mudou, o que é o que mantém esses services e
    seus testes intactos.

    Atenção: `model_copy(update=...)` não valida nem coage tipos. O cast de Numeric→float das
    temperaturas é obrigatório aqui, senão um Decimal vaza para `ChatOpenAI(temperature=...)` e
    para a borda HTTP.
    """
    if config is None:
        return base
    return base.model_copy(
        update={
            "DAILY_ANALYSIS_LIMIT_PER_OWNER": config.daily_analysis_limit_per_owner,
            "ASSISTANT_DAILY_MESSAGE_LIMIT": config.assistant_daily_message_limit,
            "OPENAI_MODEL": config.analysis_model,
            "OPENAI_TEMPERATURE": float(config.analysis_temperature),
            "ASSISTANT_CHAT_MODEL": config.assistant_model,
            "ASSISTANT_CHAT_TEMPERATURE": float(config.assistant_temperature),
        }
    )


class RuntimeSettingsService:
    def __init__(
        self,
        repo: RuntimeSettingsRepository,
        user_repo: UserRepository,
        price_repo: AiPriceRepository,
        settings: Settings,
    ) -> None:
        self.repo = repo
        self.user_repo = user_repo
        self.price_repo = price_repo
        self.settings = settings

    def get_config(self) -> RuntimeSettingsResponse:
        return self._to_response(self.repo.get())

    def update_config(
        self, *, current_user: User, payload: RuntimeSettingsIn
    ) -> RuntimeSettingsResponse:
        config = self.repo.update(
            updated_by_id=current_user.id,
            daily_analysis_limit_per_owner=payload.daily_analysis_limit_per_owner,
            assistant_daily_message_limit=payload.assistant_daily_message_limit,
            analysis_model=payload.analysis_model.strip(),
            analysis_temperature=payload.analysis_temperature,
            assistant_model=payload.assistant_model.strip(),
            assistant_temperature=payload.assistant_temperature,
        )
        return self._to_response(config)

    def test_model(self, *, model: str, temperature: float | None) -> None:
        """Levanta ModelProbeError — a rota traduz para 400."""
        probe_chat_model(
            model=model.strip(), temperature=temperature, api_key=self.settings.OPENAI_API_KEY
        )

    # --- internos ---

    def _to_response(self, config: RuntimeSettings | None) -> RuntimeSettingsResponse:
        """Com a linha ausente, devolve os defaults do ambiente em vez de 404: a tela precisa
        mostrar o que está valendo de fato, e o que está valendo é o fallback."""
        effective = build_effective_settings(self.settings, config)

        updated_by_name: str | None = None
        if config is not None and config.updated_by_id is not None:
            editor = self.user_repo.get(config.updated_by_id)
            updated_by_name = editor.name if editor is not None else None

        return RuntimeSettingsResponse(
            daily_analysis_limit_per_owner=effective.DAILY_ANALYSIS_LIMIT_PER_OWNER,
            assistant_daily_message_limit=effective.ASSISTANT_DAILY_MESSAGE_LIMIT,
            analysis_model=effective.OPENAI_MODEL,
            analysis_temperature=effective.OPENAI_TEMPERATURE,
            assistant_model=effective.ASSISTANT_CHAT_MODEL,
            assistant_temperature=effective.ASSISTANT_CHAT_TEMPERATURE,
            reasoning_model_prefixes=list(REASONING_MODEL_PREFIXES),
            analysis_model_priced=self._has_price(effective.OPENAI_MODEL),
            assistant_model_priced=self._has_price(effective.ASSISTANT_CHAT_MODEL),
            updated_at=config.updated_at if config is not None else None,
            updated_by_name=updated_by_name,
        )

    def _has_price(self, model: str) -> bool:
        price = self.price_repo.resolve(
            model=model, operation=AiUsageOperation.CHAT, on_date=date.today()
        )
        return price is not None
