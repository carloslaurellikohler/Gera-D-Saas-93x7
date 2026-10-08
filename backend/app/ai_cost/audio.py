"""Duração de áudio/vídeo via ffprobe, para custear Whisper.

Whisper é faturado por minuto de áudio, não por token. A resposta `verbose_json` que a
engine recebe traz `duration`, mas o whisper_loader descarta o objeto inteiro
(engine/src/gera_d_engine/ingestion/whisper_loader.py:36) e `engine/` não pode ser
modificada — então medimos o arquivo aqui.

Medir o arquivo ORIGINAL é correto mesmo quando audio_chunking fatia em pedaços de 15 min:
os chunks particionam o áudio, então a soma das durações é a duração original, e o número
de chamadas HTTP não altera a fatura.

`ffprobe` vem no pacote `ffmpeg`, já instalado em backend/Dockerfile e usado pelo mesmo
worker em audio_chunking.py.

Política de erro deliberadamente OPOSTA à de audio_chunking._extract_and_split: lá, ffmpeg
falhando deve reprovar a análise (sem áudio não há o que analisar); aqui, qualquer falha
devolve None e a análise segue — contabilizar custo nunca reprova nada.
"""

from __future__ import annotations

import logging
import subprocess
from decimal import Decimal, InvalidOperation
from pathlib import Path

log = logging.getLogger(__name__)

_FFPROBE_ARGS = (
    "-v",
    "error",
    "-show_entries",
    "format=duration",
    "-of",
    "default=noprint_wrappers=1:nokey=1",
)


def probe_duration_seconds(file_path: Path, *, timeout_seconds: int = 60) -> Decimal | None:
    """Duração em segundos, ou None em qualquer falha (ffprobe ausente, arquivo inválido,
    timeout, saída não numérica)."""
    try:
        completed = subprocess.run(
            ["ffprobe", *_FFPROBE_ARGS, str(file_path)],
            check=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
        duration = Decimal(completed.stdout.decode().strip())
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        InvalidOperation,
        UnicodeDecodeError,
        ValueError,
    ):
        log.warning("ffprobe nao conseguiu medir a duracao de %s", file_path, exc_info=True)
        return None

    if duration <= 0:
        return None
    return duration
