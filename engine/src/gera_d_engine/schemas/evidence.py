"""Evidência estruturada — seção 22 da especificação: criterion → finding → evidence →
response_behavior → impact. Toda conclusão relevante deve ser rastreável até aqui."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class EvidenceBasis(str, Enum):
    """Seção 15 — evidência versus inferência. A solução nunca preenche lacunas com suposição."""

    EVIDENCIA = "evidencia"
    INFERENCIA_RAZOAVEL = "inferencia_razoavel"
    INFORMACAO_INSUFICIENTE = "informacao_insuficiente"


class Evidence(BaseModel):
    criterion: str = Field(description="Chave do critério ao qual esta evidência se refere.")
    finding: str = Field(description="O que foi observado, em uma frase.")
    evidence: str = Field(description="Trecho ou paráfrase fiel da transcrição que sustenta o finding.")
    response_behavior: str = Field(description="O que o CS fez (ou deixou de fazer) em resposta.")
    impact: str = Field(description="Consequência prática observada ou provável dessa resposta.")
    basis: EvidenceBasis = EvidenceBasis.EVIDENCIA
