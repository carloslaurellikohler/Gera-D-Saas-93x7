from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.analysis import Analysis
from app.models.methodology import (
    Calibrator,
    Methodology,
    MethodologyAnchor,
    MethodologyAnchorExample,
    MethodologyCategory,
    MethodologyEligibilityRule,
    MethodologyStatus,
    MethodologySubdimension,
)

# Carregadas juntas em toda leitura de uma versão: o calibration_builder precisa das seis
# coleções para compilar o prompt, e uma análise não pode pagar N+1 por isso.
_ALL_CHILDREN = (
    Methodology.categories,
    Methodology.calibrators,
    Methodology.anchors,
    Methodology.anchor_examples,
    Methodology.subdimensions,
    Methodology.eligibility_rules,
)


class MethodologyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, methodology: Methodology) -> Methodology:
        self.db.add(methodology)
        self.db.commit()
        self.db.refresh(methodology)
        return methodology

    def get(self, methodology_id: uuid.UUID) -> Methodology | None:
        stmt = (
            select(Methodology)
            .where(Methodology.id == methodology_id)
            .options(*(selectinload(child) for child in _ALL_CHILDREN))
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_published(self) -> Methodology | None:
        stmt = (
            select(Methodology)
            .where(Methodology.status == MethodologyStatus.PUBLISHED)
            .options(*(selectinload(child) for child in _ALL_CHILDREN))
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_summaries(self) -> list[Methodology]:
        stmt = select(Methodology).order_by(Methodology.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def update_draft(
        self,
        methodology_id: uuid.UUID,
        *,
        calibration_version: str,
        methodology_name: str,
        project: str,
        content: dict,
        categories: list[dict],
        calibrators: list[dict],
        anchors: list[dict],
        anchor_examples: list[dict],
        subdimensions: list[dict],
        eligibility_rules: list[dict],
    ) -> Methodology | None:
        """Edição de rascunho = substituir tudo (campos + filhas) numa única
        transação — mais simples e seguro do que diff parcial. Limpa e dá flush nas
        coleções antes de inserir as novas linhas: sem isso, o SQLAlchemy pode emitir
        os INSERTs das novas categorias/calibradores antes dos DELETEs dos órfãos
        (mesmo nível de dependência, mesma tabela), o que colide com
        uq_methodology_category_key/uq_calibrator_key sempre que a nova versão reusa
        uma key já existente (ex.: editar um rascunho clonado de outra versão)."""
        methodology = self.get(methodology_id)
        if methodology is None:
            return None
        methodology.calibration_version = calibration_version
        methodology.methodology_name = methodology_name
        methodology.project = project
        methodology.content = content

        methodology.categories = []
        methodology.calibrators = []
        methodology.anchors = []
        methodology.anchor_examples = []
        methodology.subdimensions = []
        methodology.eligibility_rules = []
        self.db.flush()

        methodology.categories = [MethodologyCategory(**category) for category in categories]
        methodology.calibrators = [Calibrator(**calibrator) for calibrator in calibrators]
        methodology.anchors = [MethodologyAnchor(**anchor) for anchor in anchors]
        methodology.anchor_examples = [MethodologyAnchorExample(**example) for example in anchor_examples]
        methodology.subdimensions = [MethodologySubdimension(**sub) for sub in subdimensions]
        methodology.eligibility_rules = [MethodologyEligibilityRule(**rule) for rule in eligibility_rules]
        self.db.commit()
        self.db.refresh(methodology)
        return methodology

    def publish(self, methodology_id: uuid.UUID, *, published_at) -> Methodology:
        """Arquiva a PUBLISHED atual (se houver) e publica a nova, na mesma
        transação — arquivar primeiro garante que o índice parcial único nunca vê
        duas linhas PUBLISHED ao mesmo tempo no caminho feliz. Mutação via ORM (não
        UPDATE em massa via Core) para manter o identity map da sessão consistente:
        quem já tinha a versão antiga carregada enxerga o novo status sem precisar
        de um refresh/expire manual. Uma corrida real entre duas publicações
        concorrentes (duas transações distintas) ainda pode violar o índice parcial
        — o IntegrityError sobe para o service traduzir em 409."""
        previous = self.db.execute(
            select(Methodology).where(Methodology.status == MethodologyStatus.PUBLISHED)
        ).scalar_one_or_none()
        if previous is not None and previous.id != methodology_id:
            previous.status = MethodologyStatus.ARCHIVED
            previous.archived_at = published_at
            self.db.flush()

        methodology = self.get(methodology_id)
        methodology.status = MethodologyStatus.PUBLISHED
        methodology.published_at = published_at
        self.db.commit()
        self.db.refresh(methodology)
        return methodology

    def delete_draft(self, methodology_id: uuid.UUID) -> None:
        methodology = self.db.get(Methodology, methodology_id)
        if methodology is not None:
            self.db.delete(methodology)
            self.db.commit()

    def is_referenced_by_analysis(self, methodology_id: uuid.UUID) -> bool:
        stmt = select(Analysis.id).where(Analysis.methodology_version_id == methodology_id).limit(1)
        return self.db.execute(stmt).first() is not None

    def get_label_color_map(self) -> dict[str, str]:
        """Mapa label -> color de TODAS as versões (qualquer status), porque análises
        antigas referenciam labels de versões já arquivadas."""
        stmt = select(Calibrator.label, Calibrator.color)
        return {label: color.value for label, color in self.db.execute(stmt).all()}
