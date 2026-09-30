"""Fixture de um AnalysisResult completo, sem chamar a API — usada por testes unitários de
renderização e persistência."""

from __future__ import annotations

from gera_d_engine.schemas.analysis import (
    AnalysisResult,
    ConsequenceAnalysis,
    CriterionScore,
    DevelopmentItem,
    PbCommercialPotential,
    PbContext,
    PillarScore,
    ResultPotential,
    SuggestedQuestion,
    TrainingNote,
)
from gera_d_engine.schemas.evidence import Evidence, EvidenceBasis

_CRITERIA = [
    ("posicionamento", "Posicionamento", 8.0),
    ("conexao", "Conexão", 8.4),
    ("sondagem", "Sondagem", 6.5),
    ("direcionamento", "Direcionamento", 7.1),
    ("encaminhamento", "Encaminhamento", 5.9),
    ("eficiencia_conducao", "Eficiência da Condução", 6.2),
]


def build_sample_result() -> AnalysisResult:
    scores_by_criterion = [
        CriterionScore(
            key=key,
            label=label,
            score=score,
            reading=f"Leitura curta de {label}.",
            analysis=f"Análise detalhada de {label} com base na conversa.",
            evidences=[
                Evidence(
                    criterion=key,
                    finding=f"Achado sobre {label}.",
                    evidence="Trecho ilustrativo da transcrição.",
                    response_behavior="O CS respondeu de determinada forma.",
                    impact="Isso gerou certo impacto na condução.",
                    basis=EvidenceBasis.EVIDENCIA,
                )
            ],
        )
        for key, label, score in _CRITERIA
    ]

    return AnalysisResult(
        cs_id="alexandre_marques",
        cs_name="Alexandre Marques",
        pb_id="francibele_ratzlaff",
        pb_name="Francibele Ratzlaff",
        interaction_id="test-interaction-001",
        interaction_date="2026-01-15",
        interaction_type="Onboarding / Boas-vindas",
        duration="Não informada na transcrição",
        scores_by_criterion=scores_by_criterion,
        pilar_93_score=PillarScore(key="pilar_93", label="Pilar 93", score=7.8, analysis="Boa presença e confiança."),
        pilar_7_score=PillarScore(key="pilar_7", label="Pilar 7", score=6.4, analysis="Conteúdo consistente, mas extenso."),
        computed_average=7.02,
        overall_score=7.0,
        overall_band_label="Atenção",
        overall_classification_text="Atenção: boa base relacional e técnica, com baixa conversão do potencial em plano de ativação",
        executive_diagnosis="Alexandre conduz o onboarding com segurança, mas converte pouco o potencial em plano de ativação.",
        general_reading="A conversa demonstra boa conexão inicial, mas o roteiro permanece amplo demais para o perfil sênior do PB.",
        result_potential=ResultPotential(level="Médio", justification="Amplia conhecimento, mas não converte oportunidades em pipeline."),
        pb_commercial_potential=PbCommercialPotential(
            level="Alto",
            justification="Mais de 18 anos de experiência e relacionamentos de alta renda.",
            limitations="Não é possível quantificar carteira ou disponibilidade real.",
        ),
        strengths=[DevelopmentItem(title="Segurança", description="Transmite domínio técnico.", basis=EvidenceBasis.EVIDENCIA)],
        risks=[DevelopmentItem(title="Onboarding longo", description="Perfil sênior recebe roteiro padrão.", basis=EvidenceBasis.INFERENCIA_RAZOAVEL)],
        missed_opportunities=[DevelopmentItem(title="Mapear rede", description="Ex-clientes não foram mapeados.", basis=EvidenceBasis.EVIDENCIA)],
        suggested_questions=[SuggestedQuestion(question="Quais oportunidades estão mais maduras hoje?", rationale="PB citou negócios deixados na mesa.")],
        executive_recommendation="Reduzir o roteiro padrão e fechar a conversa com plano de ativação.",
        training_recommendation=TrainingNote(
            competency_to_develop="Sondagem estruturada",
            observed_behavior="Reconhece sinais, mas não aprofunda.",
            expected_behavior="Transformar sinais em diagnóstico de carteira.",
            competencies_to_preserve=["Segurança", "Proximidade", "Domínio técnico"],
        ),
        final_evaluation="Boa base relacional e técnica, porém com baixa conversão do potencial identificado.",
        evidence_fragments=[e for c in scores_by_criterion for e in c.evidences],
        pb_context=PbContext(
            seniority_signals=["18 anos de experiência", "Passagem por XP/Manchester"],
            commercial_signals=["Clientes de alta renda", "Rede em Miami"],
            needs_and_opportunities=["Home Equity", "Consignado"],
            availability_notes="Mantém vínculo CLT em outra empresa.",
            basis_notes="Sinais de experiência são evidência explícita; volume de carteira é informação insuficiente.",
        ),
        consequence_analysis=ConsequenceAnalysis(
            what_was_produced=["PB conhece melhor o portfólio Franq."],
            what_was_missed=["Nenhum plano de ativação foi registrado."],
            narrative="A conversa informa bastante, mas não converte sinais em próximos passos.",
        ),
        model_version="gera-d-engine/0.1.0-test",
        calibration_version="93x7 Franq | Calibration v1.0",
        generated_at="2026-01-15T12:00:00+00:00",
    )
