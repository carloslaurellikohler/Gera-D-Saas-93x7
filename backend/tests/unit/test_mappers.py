from __future__ import annotations

from datetime import date

from app.engine_integration.mappers import (
    build_input_metadata,
    compose_interaction_type,
    minutes_to_engine_duration,
    slugify,
)
from app.models.analysis import Analysis


def test_slugify_strips_accents_and_spaces():
    assert slugify("João Silva") == "joao-silva"


def test_slugify_empty_falls_back():
    assert slugify("   ") == "sem-nome"


def test_minutes_to_engine_duration_none():
    assert minutes_to_engine_duration(None) is None


def test_minutes_to_engine_duration_converts_seconds_to_minutes():
    assert minutes_to_engine_duration(45 * 60) == "45 min"


def test_compose_interaction_type_normal_objective():
    assert compose_interaction_type("Onboarding", None) == "Onboarding"


def test_compose_interaction_type_outro_with_complement():
    assert compose_interaction_type("Outro", "Kickoff de projeto") == "Outro: Kickoff de projeto"


def test_compose_interaction_type_outro_without_complement():
    assert compose_interaction_type("Outro", None) == "Outro"


def test_build_input_metadata_maps_all_fields():
    analysis = Analysis(
        participant_name="João Silva",
        objective="Onboarding",
        input_type="txt",
        interaction_id="abc-123",
        interaction_date=date(2026, 1, 15),
        duration_seconds=45 * 60,
    )

    metadata = build_input_metadata(analysis, cs_id="cs-1", cs_name="Consultor GerAD")

    assert metadata.cs_id == "cs-1"
    assert metadata.cs_name == "Consultor GerAD"
    assert metadata.pb_id == "joao-silva"
    assert metadata.pb_name == "João Silva"
    assert metadata.interaction_id == "abc-123"
    assert metadata.interaction_date == "2026-01-15"
    assert metadata.interaction_type == "Onboarding"
    assert metadata.duration == "45 min"


def test_build_input_metadata_defaults_interaction_date_to_today():
    analysis = Analysis(
        participant_name="Maria",
        objective="Feedback",
        input_type="txt",
        interaction_id="abc-124",
    )

    metadata = build_input_metadata(analysis, cs_id="cs-1", cs_name="Consultor GerAD")

    assert metadata.interaction_date == date.today().isoformat()
