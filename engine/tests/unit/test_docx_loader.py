from pathlib import Path

from gera_d_engine.ingestion.docx_loader import load_docx

EXAMPLE_DOCX = Path(__file__).resolve().parents[3] / "docs" / "exemplo1.docx"


def test_load_docx_identifies_only_real_speakers():
    transcript = load_docx(EXAMPLE_DOCX)

    assert transcript.is_diarized is True
    assert transcript.source_kind == "texto_transcrito"

    speakers = {t.speaker for t in transcript.turns}
    assert speakers == {"Alexandre Marques", "Bele Ratzlaff"}


def test_load_docx_keeps_section_1_as_summary():
    transcript = load_docx(EXAMPLE_DOCX)

    assert transcript.raw_summary is not None
    assert "onboarding" in transcript.raw_summary.lower()
    # Bullet headings from a seção 1 (ex.: "Consórcio:") não devem virar falas.
    assert "Consórcio" not in {t.speaker for t in transcript.turns}


def test_load_docx_first_and_last_turn():
    transcript = load_docx(EXAMPLE_DOCX)

    assert transcript.turns[0].speaker == "Alexandre Marques"
    assert transcript.turns[0].text.startswith("Boa tarde")
    assert transcript.turns[-1].text.strip() == "Tchau!"
