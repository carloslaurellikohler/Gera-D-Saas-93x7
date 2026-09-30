"""Funções puras que traduzem entre o domínio do backend (Analysis) e o contrato da
engine (InputMetadata). cs_id/cs_name entram como parâmetros explícitos — nunca lidos
diretamente de config aqui — para que trocar por "usuário autenticado" no futuro seja
uma mudança pontual no ponto de chamada (AnalysisService), não um refactor desta função."""

from __future__ import annotations

import re
import unicodedata
from datetime import date

from gera_d_engine.schemas.transcript import InputMetadata

from app.models.analysis import Analysis


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "sem-nome"


def minutes_to_engine_duration(duration_seconds: int | None) -> str | None:
    if duration_seconds is None:
        return None
    return f"{duration_seconds // 60} min"


def compose_interaction_type(objective: str, complement: str | None) -> str:
    if objective == "Outro" and complement:
        return f"Outro: {complement}"
    return objective


def build_input_metadata(analysis: Analysis, *, cs_id: str, cs_name: str) -> InputMetadata:
    return InputMetadata(
        cs_id=cs_id,
        cs_name=cs_name,
        pb_id=slugify(analysis.participant_name),
        pb_name=analysis.participant_name,
        interaction_id=analysis.interaction_id,
        interaction_date=(analysis.interaction_date or date.today()).isoformat(),
        interaction_type=compose_interaction_type(analysis.objective, analysis.objective_complement),
        duration=minutes_to_engine_duration(analysis.duration_seconds),
    )
