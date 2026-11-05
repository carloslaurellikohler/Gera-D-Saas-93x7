"""Nota geral ponderada (Fase 9).

Até a V1 a nota geral era puro julgamento holístico da IA. O Manual de Calibração V2.1
fixou pesos por critério (Posicionamento 15%, Conexão 15%, Sondagem 20%, Direcionamento
20%, Encaminhamento 15%, Eficiência 15%) e o produto passou a aplicá-los — os pesos são
versionados junto da metodologia, então mudar de ideia é publicar outra versão, não mexer
em código.

O julgamento original da IA NUNCA é descartado: volta no retorno desta função e é gravado
em Analysis.holistic_overall_score/holistic_overall_band_label. O próprio Manual trata a
fórmula como "hipótese técnica a validar contra histórico" (seção 26), então o dado que
permite questioná-la precisa sobreviver.

Mora em engine_integration/ porque opera sobre o AnalysisResult pydantic da engine — é
fronteira com a engine, não regra de negócio de serviço. A engine segue intocada: a
ponderação acontece depois de run_pipeline e antes de export_reports, de forma que os
PDFs já saem com a nota oficial sem que rendering/ precise saber disso."""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal

from gera_d_engine.calibration import Calibration
from gera_d_engine.schemas.analysis import AnalysisResult

log = logging.getLogger(__name__)


def apply_weighted_overall(
    result: AnalysisResult, calibration: Calibration
) -> tuple[float | None, str | None]:
    """Sobrescreve `overall_score`/`overall_band_label` com a soma ponderada e devolve o
    par holístico original (score, band_label) para auditoria.

    Devolve (None, None) e não mexe em nada quando a versão não tem pesos — uma
    metodologia anterior à V2.1 continua com a nota holística, e análises antigas
    permanecem reproduzíveis."""
    weights = calibration.raw.get("criterion_weights") or {}
    total_weight = sum(float(w) for w in weights.values())
    if total_weight <= 0:
        return None, None

    scores = {criterion.key: criterion.score for criterion in result.scores_by_criterion}
    missing = set(weights) - set(scores)
    if missing:
        # Não degradar em silêncio para uma nota calculada sobre parte dos critérios: a
        # nota holística da IA é melhor do que uma ponderação incompleta.
        log.warning("pesos sem nota correspondente (%s); mantendo a nota holística", sorted(missing))
        return None, None

    holistic_score = result.overall_score
    holistic_band_label = result.overall_band_label

    # Soma em Decimal, e não em float: acumular 0,15*9 + 0,20*5 + ... em binário produz
    # 6,6499999999999995 para o que deveria ser 6,65, e aí o arredondamento devolve 6,6.
    # ROUND_HALF_UP pela mesma razão — o bancário do Python levaria 7,95 para 7,9, e numa
    # nota que define a faixa do farol essa surpresa chega ao relatório do usuário.
    weighted = sum(
        (Decimal(str(scores[key])) * Decimal(str(weight)) for key, weight in weights.items()),
        start=Decimal(0),
    ) / Decimal(str(total_weight))
    result.overall_score = float(weighted.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    result.overall_band_label = calibration.classify_band(result.overall_score).label

    return holistic_score, holistic_band_label
