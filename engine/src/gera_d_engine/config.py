"""Configuração do motor: variáveis de ambiente e versão do motor.

model_version (a versão do motor em si) e calibration_version (a versão da régua/critérios,
carregada de calibration/v1.yaml) são gravados em todo AnalysisResult, conforme a seção 20/26
da especificação — resultados de versões diferentes nunca são tratados como equivalentes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ENGINE_VERSION = "gera-d-engine/0.1.0"

CALIBRATION_DIR = Path(__file__).parent / "calibration"
DEFAULT_CALIBRATION_FILE = CALIBRATION_DIR / "v1.yaml"

TEMPLATES_DIR = Path(__file__).parent / "rendering" / "templates"


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_model: str
    openai_temperature: float

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
            openai_temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
        )


def get_settings() -> Settings:
    return Settings.load()
