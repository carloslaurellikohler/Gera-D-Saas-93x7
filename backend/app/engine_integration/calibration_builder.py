"""Única ponte entre Methodology (Postgres, Fase 7) e o shape Calibration esperado por
gera_d_engine. Sempre que um novo campo global for lido por pipeline/prompts.py ou
pipeline/nodes/*.py, ele precisa existir em Methodology.content com a mesma chave — o
schema MethodologyContentIn (Fase 9) é quem garante isso na borda, já que aqui não há
validação.

Desde a Fase 9 este módulo não é mais um tradutor 1:1: ele COMPILA. O racional da
metodologia V2.1 (âncoras observáveis 0–10, exemplos ancorados, rubrica de subdimensões
0–4, regras de elegibilidade de faixa) vive em tabelas próprias, mas a engine lê um
conjunto FIXO de slots de texto — a allowlist de pipeline/nodes/behavioral_analysis.py
linha 15 e as chaves de pipeline/prompts.py. Compilar aqui é o que permite refinar todo
o system prompt mantendo o pacote engine/ intocado, que é a regra de ouro do projeto.

Mapa dos 7 slots por critério:
    description       <- description + central_question
    good_performance  <- positive_evidence
    risks             <- what_it_is_not + negative_evidence
    calibration_note  <- âncoras 2/4/6/8/10 + exemplos ancorados
    critical_rule     <- regras de elegibilidade (do critério + transversais)
    desired_structure <- rubrica de subdimensões 0–4
    cross_impact      <- cross_impact_text

Versões anteriores à V2.1 não têm as tabelas preenchidas; cada bloco é omitido quando
vazio e `extra` segue como fallback, para que uma versão arquivada continue reproduzível."""

from __future__ import annotations

from collections import defaultdict

from gera_d_engine.calibration import Calibration, ScoreBand

from app.models.methodology import (
    AnchorScope,
    EligibilityEffect,
    Methodology,
    MethodologyAnchor,
    MethodologyAnchorExample,
    MethodologyCategory,
    MethodologyEligibilityRule,
    MethodologySubdimension,
)

_TRANSVERSAL = MethodologyEligibilityRule.TRANSVERSAL_SCOPE_KEY


def _format_anchors(anchors: list[MethodologyAnchor]) -> str:
    return "\n".join(f"{a.level} — {a.descriptor.strip()}" for a in sorted(anchors, key=lambda a: a.level))


def _format_examples(examples: list[MethodologyAnchorExample]) -> str:
    blocks: list[str] = []
    for example in sorted(examples, key=lambda e: (e.level, e.order_index)):
        lines = [f"Nota {example.level}:"]
        if example.scenario:
            lines.append(f"  Cenário: {example.scenario.strip()}")
        if example.quote:
            lines.append(f'  Fala: "{example.quote.strip()}"')
        lines.append(f"  Por quê: {example.rationale.strip()}")
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


def _format_subdimensions(subdimensions: list[MethodologySubdimension]) -> str:
    blocks: list[str] = []
    for sub in sorted(subdimensions, key=lambda s: s.order_index):
        levels = "\n".join(f"  {level} — {descriptor.strip()}" for level, descriptor in enumerate(sub.levels))
        blocks.append(f"{sub.name}:\n{levels}")
    return "\n".join(blocks)


def _format_eligibility(rules: list[MethodologyEligibilityRule]) -> str:
    lines: list[str] = []
    for rule in sorted(rules, key=lambda r: r.order_index):
        condition = rule.condition.strip().rstrip(".")
        if rule.effect is EligibilityEffect.CAP:
            cap = f"{rule.max_score:.1f}".replace(".", ",")
            lines.append(f"- {condition} → nota no máximo {cap}.")
        else:
            lines.append(f"- {condition}.")
    return "\n".join(lines)


def _build_criterion(
    category: MethodologyCategory,
    *,
    anchors: list[MethodologyAnchor],
    examples: list[MethodologyAnchorExample],
    subdimensions: list[MethodologySubdimension],
    rules: list[MethodologyEligibilityRule],
) -> dict:
    # `extra` primeiro: o dado estruturado sobrescreve o legado quando existe, e uma
    # versão antiga sem âncoras continua produzindo exatamente o prompt que produzia.
    criterion: dict = {"label": category.label, **category.extra}

    if category.central_question:
        criterion["description"] = (
            f"{category.description.strip()}\nPergunta central: {category.central_question.strip()}"
        )
    else:
        criterion["description"] = category.description

    if category.positive_evidence:
        # Prefixo em português porque a engine imprime o nome do slot cru no prompt
        # ("good_performance: ..."), e o valor sozinho não diria do que se trata.
        criterion["good_performance"] = f"Evidências positivas: {category.positive_evidence.strip()}"

    risks: list[str] = []
    if category.what_it_is_not:
        risks.append(f"NÃO significa: {category.what_it_is_not.strip()}")
    if category.negative_evidence:
        risks.append(f"Evidências negativas: {category.negative_evidence.strip()}")
    if risks:
        criterion["risks"] = "\n".join(risks)

    if category.cross_impact_text:
        criterion["cross_impact"] = category.cross_impact_text.strip()

    note: list[str] = []
    if anchors:
        note.append(f"Âncoras observáveis (use-as como régua, não arbitre a nota):\n{_format_anchors(anchors)}")
    if examples:
        note.append(f"Exemplos ancorados (nível de qualidade esperado, não texto a procurar):\n{_format_examples(examples)}")
    if note:
        criterion["calibration_note"] = "\n\n".join(note)

    if rules:
        criterion["critical_rule"] = (
            "Elegibilidade de faixa — estas condições impedem determinadas notas, e boas "
            f"evidências em outros pontos não as neutralizam:\n{_format_eligibility(rules)}"
        )

    if subdimensions:
        criterion["desired_structure"] = (
            "Rubrica de auditoria 0–4 (instrumento de refinamento dentro da âncora, nunca "
            f"substituto dela; não calcular a nota pela média das subdimensões):\n{_format_subdimensions(subdimensions)}"
        )

    return criterion


def _compile_pillars(content: dict, anchors_by_scope: dict[str, list[MethodologyAnchor]]) -> dict | None:
    """Anexa as âncoras 0–10 de cada pilar à sua description, que é o que
    nodes/behavioral_analysis.py interpola. Os pilares não são critérios e não têm peso:
    93 e 7 são dimensões conceituais (Manual V2.1, seção 3)."""
    pillars = content.get("pillars")
    if not isinstance(pillars, dict):
        return pillars

    compiled = {key: dict(value) if isinstance(value, dict) else value for key, value in pillars.items()}
    for pillar_key in ("pilar_93", "pilar_7"):
        pillar = compiled.get(pillar_key)
        anchors = anchors_by_scope.get(pillar_key, [])
        if not isinstance(pillar, dict) or not anchors:
            continue
        pillar["description"] = (
            f"{pillar['description'].strip()}\n"
            f"Âncoras do {pillar.get('label', pillar_key)}:\n{_format_anchors(anchors)}"
        )
    return compiled


def _compile_final_score_rule(content: dict, categories: list[MethodologyCategory]) -> str:
    """Declara os pesos no prompt (Fase 9). A nota geral passou a ser calculada pelo
    backend em engine_integration/score_resolver.py; sem informar os pesos aqui, a IA
    narraria uma faixa (overall_justification, overall_classification_text) incoerente
    com o número que o relatório exibe."""
    rule = str(content.get("final_score_rule", "")).strip()
    weighted = [c for c in sorted(categories, key=lambda c: c.order_index) if float(c.weight) > 0]
    if not weighted:
        return rule

    weights = "; ".join(f"{c.label} {float(c.weight) * 100:.0f}%" for c in weighted)
    return (
        f"{rule}\n"
        "A nota geral desta versão é a soma ponderada das notas por critério, com os pesos: "
        f"{weights}. Não é média simples. Produza overall_score já coerente com essa "
        "ponderação e justifique o que puxou a nota para cima ou para baixo."
    )


def build_calibration(methodology: Methodology) -> Calibration:
    anchors_by_scope: dict[str, list[MethodologyAnchor]] = defaultdict(list)
    for anchor in methodology.anchors:
        anchors_by_scope[anchor.scope_key].append(anchor)

    examples_by_criterion: dict[str, list[MethodologyAnchorExample]] = defaultdict(list)
    for example in methodology.anchor_examples:
        examples_by_criterion[example.criterion_key].append(example)

    subdimensions_by_criterion: dict[str, list[MethodologySubdimension]] = defaultdict(list)
    for subdimension in methodology.subdimensions:
        subdimensions_by_criterion[subdimension.criterion_key].append(subdimension)

    rules_by_criterion: dict[str, list[MethodologyEligibilityRule]] = defaultdict(list)
    transversal_rules: list[MethodologyEligibilityRule] = []
    for rule in methodology.eligibility_rules:
        if rule.scope_key == _TRANSVERSAL:
            transversal_rules.append(rule)
        else:
            rules_by_criterion[rule.scope_key].append(rule)

    criteria: dict[str, dict] = {}
    for category in sorted(methodology.categories, key=lambda c: c.order_index):
        criterion_anchors = [a for a in anchors_by_scope.get(category.key, []) if a.scope is AnchorScope.CRITERION]
        criteria[category.key] = _build_criterion(
            category,
            anchors=criterion_anchors,
            examples=examples_by_criterion.get(category.key, []),
            subdimensions=subdimensions_by_criterion.get(category.key, []),
            rules=rules_by_criterion.get(category.key, []) + transversal_rules,
        )

    score_bands_raw = [
        {
            "min": calibrator.min,
            "max": calibrator.max,
            "key": calibrator.key,
            "label": calibrator.label,
            "color": calibrator.color.value,
        }
        for calibrator in sorted(methodology.calibrators, key=lambda c: c.order_index)
    ]

    content = dict(methodology.content)
    compiled_pillars = _compile_pillars(content, anchors_by_scope)

    raw = {
        **content,
        "calibration_version": methodology.calibration_version,
        "methodology_name": methodology.methodology_name,
        "project": methodology.project,
        "criteria": criteria,
        "score_bands": score_bands_raw,
    }
    if compiled_pillars is not None:
        raw["pillars"] = compiled_pillars

    # Chave nossa, não da engine: nenhum nó a lê, mas ela viaja junto da calibração para
    # que score_resolver.py aplique os pesos da MESMA versão que gerou as notas, sem
    # reabrir o banco. Só existe quando a versão tem pesos — uma versão anterior à V2.1
    # continua produzindo exatamente o raw que sempre produziu, e sua nota geral segue
    # holística.
    weights = {
        category.key: float(category.weight)
        for category in sorted(methodology.categories, key=lambda c: c.order_index)
    }
    if any(weight > 0 for weight in weights.values()):
        raw["criterion_weights"] = weights
        if "final_score_rule" in content:
            raw["final_score_rule"] = _compile_final_score_rule(content, list(methodology.categories))

    bands = [
        ScoreBand(
            key=band["key"],
            label=band["label"],
            color=band["color"],
            min=float(band["min"]),
            max=float(band["max"]),
        )
        for band in score_bands_raw
    ]
    return Calibration(raw=raw, score_bands=bands)
