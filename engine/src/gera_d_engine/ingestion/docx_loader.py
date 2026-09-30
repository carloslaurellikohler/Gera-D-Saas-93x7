"""Leitura de transcrições já prontas em .docx/.txt (ex.: docs/exemplo1.docx).

Formato esperado (o mesmo do exemplo fornecido): um cabeçalho/resumo livre, seguido de uma seção
de transcrição com falas no padrão "Nome do Falante: texto da fala" — uma por parágrafo/linha.
Quando o documento não segue esse padrão, o conteúdo inteiro vira um único turno sem falante
identificado (is_diarized=False), e a etapa de normalização decide o que fazer.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import docx

from gera_d_engine.schemas.transcript import Transcript, TranscriptTurn

# Nome do falante: até 4 palavras capitalizadas, seguido de ":" e a fala.
_TURN_PATTERN = re.compile(
    r"^([A-ZÀ-Ý][\wÀ-ÿ'\".-]*(?:\s+[A-ZÀ-Ý][\wÀ-ÿ'\".-]*){0,3}):\s+(.+)$"
)

# Cabeçalho de seção que introduz a transcrição íntegra, ex.: "2. Transcrição Íntegra da Conversa".
# Tudo antes disso (resumo, tópicos) vira raw_summary; só depois disso tentamos casar turnos.
_TRANSCRIPT_SECTION_HEADING = re.compile(r"^\d+\.\s*Transcri[cç][aã]o\b", re.IGNORECASE)


def _split_summary_and_dialogue(lines: list[str]) -> tuple[list[str], list[str]]:
    heading_idx = None
    for i, line in enumerate(lines):
        if _TRANSCRIPT_SECTION_HEADING.match(line.strip()):
            heading_idx = i
    if heading_idx is None:
        return [], lines
    return lines[:heading_idx], lines[heading_idx + 1 :]


def _parse_lines(lines: list[str]) -> Transcript:
    pre_lines, dialogue_lines = _split_summary_and_dialogue(lines)
    summary_lines: list[str] = [line.strip() for line in pre_lines if line.strip()]
    turns: list[TranscriptTurn] = []

    for line in dialogue_lines:
        line = line.strip()
        if not line:
            continue
        match = _TURN_PATTERN.match(line)
        if match:
            speaker, text = match.group(1), match.group(2)
            turns.append(TranscriptTurn(speaker=speaker, text=text))
        elif turns:
            # Continuação de uma fala que quebrou em mais de um parágrafo.
            turns[-1].text = f"{turns[-1].text} {line}"
        else:
            summary_lines.append(line)

    # Rede de segurança: um "falante" que aparece uma única vez é provavelmente um falso
    # positivo (título de bullet, subtítulo) capturado pelo regex — funde no turno anterior
    # em vez de virar um participante fantasma da conversa.
    if turns:
        speaker_freq = Counter(t.speaker for t in turns if t.speaker)
        cleaned: list[TranscriptTurn] = []
        for turn in turns:
            if turn.speaker and speaker_freq[turn.speaker] == 1 and cleaned:
                cleaned[-1].text = f"{cleaned[-1].text} {turn.text}"
            else:
                cleaned.append(turn)
        turns = cleaned

    is_diarized = len(turns) >= 2 and len({t.speaker for t in turns if t.speaker}) >= 2
    if not turns:
        # Nenhum padrão "Nome: fala" encontrado — trata tudo como um bloco só, sem falante.
        full_text = "\n".join(summary_lines)
        turns = [TranscriptTurn(speaker=None, text=full_text)] if full_text else []
        summary_lines = []

    return Transcript(
        turns=turns,
        is_diarized=is_diarized,
        source_kind="texto_transcrito",
        raw_summary="\n".join(summary_lines) or None,
    )


def load_docx(path: str | Path) -> Transcript:
    document = docx.Document(str(path))
    lines = [p.text for p in document.paragraphs]
    return _parse_lines(lines)


def load_txt(path: str | Path) -> Transcript:
    text = Path(path).read_text(encoding="utf-8")
    return _parse_lines(text.splitlines())
