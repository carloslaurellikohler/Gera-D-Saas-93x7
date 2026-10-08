"""Constantes do FinAI que espelham valores fixos dentro de `engine/`.

Não viram Setting de propósito: transformá-las em variável de ambiente sugeriria falsamente
que são configuráveis, quando na verdade estão hardcoded na engine — que não pode ser
modificada. Se a engine mudar, estas constantes mudam junto, e o teste de contrato avisa.
"""

from __future__ import annotations

# Hardcoded em engine/src/gera_d_engine/ingestion/whisper_loader.py:31
# (`model="whisper-1"`), sem vir de config nem de env.
WHISPER_MODEL_NAME = "whisper-1"

# Extensões que de fato geram chamada ao Whisper. `.docx`/`.txt` são lidos localmente pelo
# docx_loader e não custam nada — espelha gera_d_engine.ingestion.whisper_loader
# .SUPPORTED_AUDIO_VIDEO_EXTENSIONS.
TRANSCRIBED_INPUT_TYPES = frozenset({"mp3", "mp4"})
