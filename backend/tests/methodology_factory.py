"""Payloads mínimos porém VÁLIDOS de metodologia, compartilhados pelos testes de service,
repositório e API.

Desde a Fase 9 um rascunho publicável precisa de muito mais do que 6 critérios e 4 faixas:
`content` é validado contra MethodologyContentIn (toda chave que a engine lê), os pesos
precisam somar 1 e cada critério e cada pilar precisa das 5 âncoras. Montar isso à mão em
cada arquivo de teste convidaria a cópias divergentes."""

from __future__ import annotations

from app.core.constants import CriterionKey
from app.models.methodology import AnchorScope, EligibilityEffect
from app.schemas.methodology import ANCHOR_LEVELS, PILLAR_KEYS, MethodologyDraftIn

_CRITERION_KEYS = [key.value for key in CriterionKey]

# 6 critérios com pesos que somam exatamente 1.0 (0.15 x 4 + 0.2 x 2).
_WEIGHTS = {
    "posicionamento": 0.15,
    "conexao": 0.15,
    "sondagem": 0.20,
    "direcionamento": 0.20,
    "encaminhamento": 0.15,
    "eficiencia_conducao": 0.15,
}


def valid_content() -> dict:
    return {
        "objective": "Avaliar.",
        "unit_of_analysis": "Pessoa x contexto.",
        "product_principle": "Ordem de raciocínio.",
        "contextual_analysis_principle": "Contextual, não literal.",
        "seniority_and_adaptation": "Adaptar ao perfil.",
        "individual_development_not_ranking": "Sem ranking.",
        "forbidden_behaviors": ["Avaliar por palavra-chave."],
        "evidence_basis": {
            "evidencia": "Explícito.",
            "inferencia_razoavel": "Múltiplos sinais.",
            "informacao_insuficiente": "Não sustenta.",
            "rule": "Nunca supor.",
        },
        "pillars": {
            "pilar_93": {"label": "Pilar 93", "description": "Comportamento."},
            "pilar_7": {"label": "Pilar 7", "description": "Conteúdo."},
            "rule": "Não é fórmula.",
        },
        "evidence_structure": "criterion → finding → evidence",
        "final_score_rule": "Sem média cega.",
        "result_potential": {"description": "Potencial.", "levels": ["Baixo", "Alto"]},
        "pb_commercial_potential": {
            "description": "Sinais.",
            "levels": ["Baixo", "Alto"],
            "warning": "Não inventar.",
        },
        "development_taxonomy": {
            "pontos_preservados": "Fortes.",
            "riscos": "Consequências.",
            "oportunidades_perdidas": "Possibilidades.",
        },
        "suggested_questions_rule": "Contextual.",
        "suggested_questions_examples": ["Qual oportunidade está madura?"],
        "executive_recommendation_rule": "Específica.",
        "training_notes_rule": "Síntese para T&D.",
    }


def valid_categories() -> list[dict]:
    return [
        {
            "key": key,
            "label": key.title(),
            "description": "Descrição.",
            "order_index": order_index,
            "weight": _WEIGHTS[key],
        }
        for order_index, key in enumerate(_CRITERION_KEYS)
    ]


def valid_calibrators() -> list[dict]:
    return [
        {"key": "excelente", "label": "Excelente", "color": "verde", "min": 8.0, "max": 10.0, "order_index": 0},
        {"key": "atencao", "label": "Atenção", "color": "amarelo", "min": 7.0, "max": 7.9, "order_index": 1},
        {"key": "prioritario", "label": "Prioritário", "color": "laranja", "min": 6.0, "max": 6.9, "order_index": 2},
        {"key": "critico", "label": "Crítico", "color": "vermelho", "min": 0.0, "max": 5.9, "order_index": 3},
    ]


def valid_anchors() -> list[dict]:
    """5 âncoras para cada um dos 6 critérios e dos 2 pilares — o que publish() exige."""
    anchors: list[dict] = []
    scopes = [(AnchorScope.CRITERION.value, key) for key in _CRITERION_KEYS]
    scopes += [(AnchorScope.PILLAR.value, key) for key in PILLAR_KEYS]
    for scope, scope_key in scopes:
        for level in ANCHOR_LEVELS:
            anchors.append(
                {
                    "scope": scope,
                    "scope_key": scope_key,
                    "level": level,
                    "descriptor": f"{scope_key} nível {level}.",
                    "order_index": len(anchors),
                }
            )
    return anchors


def valid_payload_dict(*, calibration_version: str = "v2") -> dict:
    """Shape JSON, para os testes de API."""
    return {
        "calibration_version": calibration_version,
        "methodology_name": "93x7®",
        "project": "Projeto Franq",
        "content": valid_content(),
        "categories": valid_categories(),
        "calibrators": valid_calibrators(),
        "anchors": valid_anchors(),
        "anchor_examples": [
            {
                "criterion_key": "sondagem",
                "level": 8,
                "quote": "Quantas demandas você encaminhou nos últimos 30 dias?",
                "rationale": "Dimensiona volume.",
                "order_index": 0,
            }
        ],
        "subdimensions": [
            {
                "criterion_key": "sondagem",
                "name": "Profundidade",
                "levels": ["não aprofunda", "superficial", "pontual", "sinais relevantes", "seletiva"],
                "order_index": 0,
            }
        ],
        "eligibility_rules": [
            {
                "scope_key": "sondagem",
                "condition": "Sem aprofundamento relevante",
                "effect": EligibilityEffect.CAP.value,
                "max_score": 7.9,
                "order_index": 0,
            }
        ],
    }


def valid_draft_payload(*, calibration_version: str = "v2") -> MethodologyDraftIn:
    return MethodologyDraftIn(**valid_payload_dict(calibration_version=calibration_version))
