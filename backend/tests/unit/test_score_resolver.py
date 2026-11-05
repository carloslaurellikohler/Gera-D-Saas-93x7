"""A nota geral ponderada (Fase 9) e, principalmente, as condições em que ela NÃO se
aplica: a ponderação nunca pode degradar em silêncio para uma nota calculada sobre parte
dos critérios, e nunca pode apagar o julgamento holístico original da IA."""

from __future__ import annotations

from gera_d_engine.calibration import Calibration, ScoreBand

from app.engine_integration.score_resolver import apply_weighted_overall

_BANDS = [
    ScoreBand(key="excelente", label="Excelente desempenho", color="verde", min=8.0, max=10.0),
    ScoreBand(key="atencao", label="Atenção", color="amarelo", min=7.0, max=7.9),
    ScoreBand(key="prioritario", label="Desenvolvimento prioritário", color="laranja", min=6.0, max=6.9),
    ScoreBand(key="critico", label="Desenvolvimento crítico", color="vermelho", min=-999.0, max=5.9),
]

_WEIGHTS = {
    "posicionamento": 0.15,
    "conexao": 0.15,
    "sondagem": 0.20,
    "direcionamento": 0.20,
    "encaminhamento": 0.15,
    "eficiencia_conducao": 0.15,
}


class _FakeCriterion:
    def __init__(self, key: str, score: float) -> None:
        self.key = key
        self.score = score


class _FakeResult:
    """Dublê do AnalysisResult: só os três campos que o resolver toca."""

    def __init__(self, scores: dict[str, float], *, overall_score: float, band_label: str) -> None:
        self.scores_by_criterion = [_FakeCriterion(key, score) for key, score in scores.items()]
        self.overall_score = overall_score
        self.overall_band_label = band_label


def _calibration(weights: dict[str, float] | None) -> Calibration:
    raw: dict = {}
    if weights is not None:
        raw["criterion_weights"] = weights
    return Calibration(raw=raw, score_bands=_BANDS)


def _all_criteria(value: float) -> dict[str, float]:
    return {key: value for key in _WEIGHTS}


def test_weighted_overall_replaces_the_score_and_reclassifies_the_band():
    # Posicionamento e Conexão altos (9,0) não salvam Sondagem/Direcionamento/
    # Encaminhamento fracos: 0,15*9 + 0,15*9 + 0,20*5 + 0,20*5 + 0,15*5 + 0,15*8 = 6,65
    result = _FakeResult(
        {
            "posicionamento": 9.0,
            "conexao": 9.0,
            "sondagem": 5.0,
            "direcionamento": 5.0,
            "encaminhamento": 5.0,
            "eficiencia_conducao": 8.0,
        },
        overall_score=8.2,
        band_label="Excelente desempenho",
    )

    holistic = apply_weighted_overall(result, _calibration(_WEIGHTS))

    assert result.overall_score == 6.7  # arredondado a uma casa
    assert result.overall_band_label == "Desenvolvimento prioritário"
    # O julgamento original da IA volta intacto, para auditoria.
    assert holistic == (8.2, "Excelente desempenho")


def test_uniform_scores_produce_the_same_score():
    result = _FakeResult(_all_criteria(7.5), overall_score=6.0, band_label="Desenvolvimento prioritário")

    apply_weighted_overall(result, _calibration(_WEIGHTS))

    assert result.overall_score == 7.5
    assert result.overall_band_label == "Atenção"


def test_version_without_weights_keeps_the_holistic_score_untouched():
    """Uma metodologia anterior à V2.1 não tem pesos — a nota segue sendo o julgamento
    holístico, e nada é gravado como 'original'."""
    result = _FakeResult(_all_criteria(7.0), overall_score=8.4, band_label="Excelente desempenho")

    assert apply_weighted_overall(result, _calibration(None)) == (None, None)
    assert result.overall_score == 8.4
    assert result.overall_band_label == "Excelente desempenho"


def test_missing_criterion_score_falls_back_to_the_holistic_score():
    """Um peso sem nota correspondente significaria ponderar sobre parte dos critérios.
    Melhor manter a nota da IA do que publicar um número silenciosamente errado."""
    partial = _all_criteria(7.0)
    del partial["sondagem"]
    result = _FakeResult(partial, overall_score=8.4, band_label="Excelente desempenho")

    assert apply_weighted_overall(result, _calibration(_WEIGHTS)) == (None, None)
    assert result.overall_score == 8.4
