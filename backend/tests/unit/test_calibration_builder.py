"""Dois contratos do calibration_builder.

1. Paridade (Fase 7): uma Methodology SEM dado estruturado precisa produzir o mesmo
   Calibration que load_calibration(calibration/v1.yaml) produzia. É o que garante que
   uma versão arquivada continua reproduzível e que a Fase 9 não alterou o passado.
2. Compilação (Fase 9): com âncoras, exemplos, subdimensões e regras cadastradas, esse
   racional precisa chegar aos slots de texto que a engine lê — é o mecanismo inteiro
   que permite refinar o system prompt sem tocar no pacote engine/."""

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


# --- Fase 9: a compilação do racional V2.1 nos slots que a engine já lê -------------
# Os testes acima garantem que uma versão SEM dado estruturado continua produzindo o raw
# de sempre. Os de baixo garantem que, com dado estruturado, ele chega ao prompt.


def _v21_methodology(db_session) -> Methodology:
    from app.models.methodology import (
        AnchorScope,
        EligibilityEffect,
        MethodologyAnchor,
        MethodologyAnchorExample,
        MethodologyEligibilityRule,
        MethodologySubdimension,
    )

    methodology = _seed_from_yaml(db_session)
    sondagem = next(c for c in methodology.categories if c.key == "sondagem")
    sondagem.central_question = "O que foi descoberto muda a conversa?"
    sondagem.what_it_is_not = "quantidade de perguntas"
    sondagem.positive_evidence = "follow-up e dimensionamento"
    sondagem.negative_evidence = "checklist cadastral"
    sondagem.weight = 1.0

    methodology.anchors = [
        MethodologyAnchor(
            scope=AnchorScope.CRITERION,
            scope_key="sondagem",
            level=level,
            descriptor=f"descritor nivel {level}",
            order_index=index,
        )
        for index, level in enumerate((2, 4, 6, 8, 10))
    ] + [
        MethodologyAnchor(
            scope=AnchorScope.PILLAR,
            scope_key="pilar_93",
            level=level,
            descriptor=f"pilar 93 nivel {level}",
            order_index=10 + index,
        )
        for index, level in enumerate((2, 4, 6, 8, 10))
    ]
    methodology.anchor_examples = [
        MethodologyAnchorExample(
            criterion_key="sondagem",
            level=8,
            scenario="PB cita clientes antigos",
            quote="Alguma demanda ainda pode ser recuperada?",
            rationale="dimensiona recuperabilidade",
            order_index=0,
        )
    ]
    methodology.subdimensions = [
        MethodologySubdimension(
            criterion_key="sondagem",
            name="Profundidade",
            levels=["nao aprofunda", "superficial", "pontual", "sinais relevantes", "seletiva"],
            order_index=0,
        )
    ]
    methodology.eligibility_rules = [
        MethodologyEligibilityRule(
            scope_key="sondagem",
            condition="Sem aprofundamento relevante",
            effect=EligibilityEffect.CAP,
            max_score=7.9,
            order_index=0,
        ),
        MethodologyEligibilityRule(
            scope_key="TRANSVERSAL",
            condition="Uma evidência isolada não justifica 10",
            effect=EligibilityEffect.NOTE,
            max_score=None,
            order_index=1,
        ),
    ]
    db_session.commit()
    db_session.refresh(methodology)
    return methodology


def test_anchors_and_examples_reach_the_criterion_calibration_note(db_session):
    criterion = build_calibration(_v21_methodology(db_session)).raw["criteria"]["sondagem"]

    note = criterion["calibration_note"]
    for level in (2, 4, 6, 8, 10):
        assert f"{level} — descritor nivel {level}" in note
    assert "PB cita clientes antigos" in note
    assert "Alguma demanda ainda pode ser recuperada?" in note


def test_eligibility_rules_become_the_critical_rule_with_the_cap_spelled_out(db_session):
    criterion = build_calibration(_v21_methodology(db_session)).raw["criteria"]["sondagem"]

    assert "Sem aprofundamento relevante → nota no máximo 7,9." in criterion["critical_rule"]
    # A regra transversal vale para todos os critérios, então entra em cada bloco.
    assert "Uma evidência isolada não justifica 10." in criterion["critical_rule"]


def test_subdimensions_become_the_desired_structure(db_session):
    criterion = build_calibration(_v21_methodology(db_session)).raw["criteria"]["sondagem"]

    assert "Profundidade:" in criterion["desired_structure"]
    assert "0 — nao aprofunda" in criterion["desired_structure"]
    assert "4 — seletiva" in criterion["desired_structure"]


def test_definition_fields_land_on_the_slots_the_engine_reads(db_session):
    criterion = build_calibration(_v21_methodology(db_session)).raw["criteria"]["sondagem"]

    assert "Pergunta central: O que foi descoberto muda a conversa?" in criterion["description"]
    assert criterion["good_performance"] == "Evidências positivas: follow-up e dimensionamento"
    assert "NÃO significa: quantidade de perguntas" in criterion["risks"]
    assert "Evidências negativas: checklist cadastral" in criterion["risks"]


def test_pillar_anchors_are_appended_to_the_pillar_description(db_session):
    pillars = build_calibration(_v21_methodology(db_session)).raw["pillars"]

    assert "10 — pilar 93 nivel 10" in pillars["pilar_93"]["description"]
    # O pilar sem âncoras cadastradas fica exatamente como estava.
    assert "Âncoras" not in pillars["pilar_7"]["description"]


def test_weights_are_exposed_and_declared_in_the_final_score_rule(db_session):
    raw = build_calibration(_v21_methodology(db_session)).raw

    assert raw["criterion_weights"]["sondagem"] == 1.0
    assert "Sondagem 100%" in raw["final_score_rule"]
    assert "soma ponderada" in raw["final_score_rule"]
