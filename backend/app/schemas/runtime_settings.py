"""Schemas da configuração operacional editável em runtime (tela /configuracoes)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RuntimeSettingsResponse(BaseModel):
    """Montado pelo service (tem campos derivados), por isso sem `from_attributes`."""

    daily_analysis_limit_per_owner: int
    assistant_daily_message_limit: int
    analysis_model: str
    analysis_temperature: float
    assistant_model: str
    assistant_temperature: float

    # A tela desabilita o campo de temperatura quando o modelo digitado é de raciocínio. A
    # lista vai no response para que o frontend use a MESMA de assistant_llm.py, em vez de
    # virar uma terceira cópia dos prefixos.
    reasoning_model_prefixes: list[str]

    # Falso quando o modelo não tem vigência de preço cadastrada: as chamadas dele vão cair em
    # cost_status=NO_PRICE no FinAI até o ADMIN cadastrar o preço em /custos-ia.
    analysis_model_priced: bool
    assistant_model_priced: bool

    # Auditoria do último editor apenas — não há histórico de alterações.
    updated_at: datetime | None
    updated_by_name: str | None


class RuntimeSettingsIn(BaseModel):
    """Escrita é do objeto inteiro (replace), não patch — a tela salva os seis campos juntos.

    As restrições de faixa ficam no Field para render 422 automático, como em AiCostConfigIn.
    """

    daily_analysis_limit_per_owner: int = Field(ge=1, le=100)
    assistant_daily_message_limit: int = Field(ge=1, le=1000)
    analysis_model: str = Field(min_length=1, max_length=120)
    analysis_temperature: float = Field(ge=0, le=2)
    assistant_model: str = Field(min_length=1, max_length=120)
    assistant_temperature: float = Field(ge=0, le=2)


class ModelTestRequest(BaseModel):
    """`model_name` e não `model`: o prefixo `model_` é namespace protegido do pydantic, e
    liberá-lo com ConfigDict(protected_namespaces=()) seria um desvio sem ganho."""

    model_name: str = Field(min_length=1, max_length=120)
    temperature: float | None = Field(default=None, ge=0, le=2)


class ModelTestResponse(BaseModel):
    ok: bool
    message: str
