"""Teste de paridade: build_calibration(Methodology do Postgres) precisa produzir o
mesmo Calibration que load_calibration(calibration/v1.yaml) produzia antes da Fase 7 —
é a rede de segurança de que o comportamento do pipeline não muda no dia da virada."""

from __future__ import annotations

from gera_d_engine.calibration import load_calibration

from app.engine_integration.calibration_builder import build_calibration
from app.models.methodology import Calibrator, FarolColor, Methodology, MethodologyCategory, MethodologyStatus

_NON_CONTENT_KEYS = {"calibration_version", "methodology_name", "project", "criteria", "score_bands"}
_CATEGORY_EXTRA_KEYS = (
    "good_performance", "risks", "calibration_note", "critical_rule", "cross_impact", "desired_structure",
)


def _seed_from_yaml(db_session) -> Methodology:
    """Reproduz, com a mesma lógica de divisão de colunas da migration de seed
    (5b77efb26e8d), a Methodology que representaria calibration/v1.yaml no Postgres."""
    raw = load_calibration().raw
    content = {key: value for key, value in raw.items() if key not in _NON_CONTENT_KEYS}

    categories = [
        MethodologyCategory(
            key=key,
            label=crit["label"],
            description=crit["description"],
            order_index=order_index,
            extra={extra_key: crit[extra_key] for extra_key in _CATEGORY_EXTRA_KEYS if extra_key in crit},
        )
        for order_index, (key, crit) in enumerate(raw["criteria"].items())
    ]
    calibrators = [
        Calibrator(
            key=band["key"],
            label=band["label"],
            color=FarolColor(band["color"]),
            min=float(band["min"]),
            max=float(band["max"]),
            order_index=order_index,
        )
        for order_index, band in enumerate(raw["score_bands"])
    ]

    methodology = Methodology(
        calibration_version=raw["calibration_version"],
        methodology_name=raw["methodology_name"],
        project=raw["project"],
        status=MethodologyStatus.PUBLISHED,
        content=content,
        categories=categories,
        calibrators=calibrators,
    )
    db_session.add(methodology)
    db_session.commit()
    db_session.refresh(methodology)
    return methodology


def test_build_calibration_raw_matches_yaml_source(db_session):
    methodology = _seed_from_yaml(db_session)

    built_raw = build_calibration(methodology).raw
    yaml_raw = load_calibration().raw

    assert built_raw == yaml_raw


def test_build_calibration_score_bands_match_yaml_source(db_session):
    methodology = _seed_from_yaml(db_session)

    built_bands = build_calibration(methodology).score_bands
    yaml_bands = load_calibration().score_bands

    assert built_bands == yaml_bands


def test_build_calibration_version_matches(db_session):
    methodology = _seed_from_yaml(db_session)

    assert build_calibration(methodology).calibration_version == load_calibration().calibration_version
