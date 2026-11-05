/**
 * Os blocos globais do prompt, que até a Fase 9 viviam invisíveis no JSONB `content` e
 * só eram editáveis por migration. Cada campo aqui é interpolado literalmente em
 * pipeline/prompts.py (preâmbulo, repetido nas 7 etapas) ou num nó específico.
 */
import type {
  Calibrator,
  FarolColor,
  MethodologyAnchor,
  MethodologyCategory,
  MethodologyContent,
  MethodologyPromptPreview,
} from "../../types/methodology";
import { PILLAR_KEYS } from "../../types/methodology";
import Collapsible from "../ui/Collapsible";
import { AnchorEditor } from "./CriteriaSection";
import { StringListField, TextAreaField, TextField } from "./fields";

type ContentPatch = (patch: Partial<MethodologyContent>) => void;

interface ContentProps {
  readOnly: boolean;
  content: MethodologyContent;
  onContentChange: ContentPatch;
}

// --- 1. identidade e escopo --------------------------------------------------------

export function IdentitySection({
  readOnly,
  content,
  onContentChange,
  calibrationVersion,
  onCalibrationVersionChange,
  methodologyName,
  project,
}: ContentProps & {
  calibrationVersion: string;
  onCalibrationVersionChange: (value: string) => void;
  methodologyName: string;
  project: string;
}) {
  return (
    <div className="methodology-section">
      <TextField
        label="Nome da versão"
        value={calibrationVersion}
        readOnly={readOnly}
        hint="Fica gravado em cada análise gerada por esta versão."
        onChange={onCalibrationVersionChange}
      />
      <div className="form-row">
        <TextField label="Metodologia" value={methodologyName} readOnly onChange={() => undefined} />
        <TextField label="Projeto" value={project} readOnly onChange={() => undefined} />
      </div>
      <TextAreaField
        label="Objetivo"
        value={content.objective ?? ""}
        readOnly={readOnly}
        rows={8}
        onChange={(objective) => onContentChange({ objective })}
      />
      <TextAreaField
        label="Unidade de análise"
        value={content.unit_of_analysis ?? ""}
        readOnly={readOnly}
        rows={8}
        hint="Pessoa × Contexto × Comportamento × Consequência, e a lista do que não confundir."
        onChange={(unit_of_analysis) => onContentChange({ unit_of_analysis })}
      />
    </div>
  );
}

// --- 2. protocolo de análise -------------------------------------------------------

export function ProtocolSection({ readOnly, content, onContentChange }: ContentProps) {
  const basis = content.evidence_basis;

  return (
    <div className="methodology-section">
      <TextAreaField
        label="Ordem de raciocínio e escala 0–10"
        value={content.product_principle ?? ""}
        readOnly={readOnly}
        rows={14}
        hint="Os nove passos até a nota e a progressão descritiva de cada ponto da escala."
        onChange={(product_principle) => onContentChange({ product_principle })}
      />
      <TextAreaField
        label="Impacto, recorrência, confiança e evidência insuficiente"
        value={content.contextual_analysis_principle ?? ""}
        readOnly={readOnly}
        rows={14}
        onChange={(contextual_analysis_principle) => onContentChange({ contextual_analysis_principle })}
      />
      <TextAreaField
        label="Adaptação por senioridade e cenário"
        value={content.seniority_and_adaptation ?? ""}
        readOnly={readOnly}
        rows={10}
        onChange={(seniority_and_adaptation) => onContentChange({ seniority_and_adaptation })}
      />
      <TextAreaField
        label="Desenvolvimento individual, não ranking"
        value={content.individual_development_not_ranking ?? ""}
        readOnly={readOnly}
        rows={5}
        onChange={(value) => onContentChange({ individual_development_not_ranking: value })}
      />

      <Collapsible title="Evidência versus inferência">
        {basis ? (
          <>
            <TextField
              label="Evidência"
              value={basis.evidencia}
              readOnly={readOnly}
              onChange={(evidencia) => onContentChange({ evidence_basis: { ...basis, evidencia } })}
            />
            <TextField
              label="Inferência razoável"
              value={basis.inferencia_razoavel}
              readOnly={readOnly}
              onChange={(v) => onContentChange({ evidence_basis: { ...basis, inferencia_razoavel: v } })}
            />
            <TextField
              label="Informação insuficiente"
              value={basis.informacao_insuficiente}
              readOnly={readOnly}
              onChange={(v) => onContentChange({ evidence_basis: { ...basis, informacao_insuficiente: v } })}
            />
            <TextAreaField
              label="Regra"
              value={basis.rule}
              readOnly={readOnly}
              rows={5}
              hint="A cadeia Evidência → Interpretação → Consequência → Alternativa."
              onChange={(rule) => onContentChange({ evidence_basis: { ...basis, rule } })}
            />
          </>
        ) : null}
        <TextField
          label="Estrutura da evidência"
          value={content.evidence_structure ?? ""}
          readOnly={readOnly}
          onChange={(evidence_structure) => onContentChange({ evidence_structure })}
        />
      </Collapsible>

      <StringListField
        label="O que nunca fazer"
        values={content.forbidden_behaviors ?? []}
        readOnly={readOnly}
        addLabel="Adicionar regra"
        hint="Entram no preâmbulo de todas as etapas. É onde moram os testes de aceitação."
        onChange={(forbidden_behaviors) => onContentChange({ forbidden_behaviors })}
      />
    </div>
  );
}

// --- 3. pilares 93 e 7 -------------------------------------------------------------

export function PillarsSection({
  readOnly,
  content,
  onContentChange,
  anchors,
  onAnchorsChange,
}: ContentProps & {
  anchors: MethodologyAnchor[];
  onAnchorsChange: (anchors: MethodologyAnchor[]) => void;
}) {
  const pillars = content.pillars;
  if (!pillars) {
    return <p className="page-subtitle">Esta versão não tem os pilares cadastrados.</p>;
  }

  return (
    <div className="methodology-section">
      <TextAreaField
        label="Regra dos pilares"
        value={pillars.rule}
        readOnly={readOnly}
        rows={5}
        hint="93 e 7 são dimensões conceituais, nunca pesos matemáticos."
        onChange={(rule) => onContentChange({ pillars: { ...pillars, rule } })}
      />
      {PILLAR_KEYS.map((key) => (
        <Collapsible key={key} title={pillars[key].label} defaultOpen>
          <TextField
            label="Nome exibido"
            value={pillars[key].label}
            readOnly={readOnly}
            onChange={(label) =>
              onContentChange({ pillars: { ...pillars, [key]: { ...pillars[key], label } } })
            }
          />
          <TextAreaField
            label="O que avalia"
            value={pillars[key].description}
            readOnly={readOnly}
            rows={5}
            onChange={(description) =>
              onContentChange({ pillars: { ...pillars, [key]: { ...pillars[key], description } } })
            }
          />
          <AnchorEditor
            readOnly={readOnly}
            scopeKey={key}
            anchors={anchors}
            onChange={onAnchorsChange}
            title={`Âncoras do ${pillars[key].label}`}
          />
        </Collapsible>
      ))}
    </div>
  );
}

// --- 4. régua de faixas e nota final ----------------------------------------------

const COLOR_HEX: Record<FarolColor, string> = {
  vermelho: "#B00020",
  laranja: "#C95800",
  amarelo: "#A87800",
  verde: "#0F7A45",
};

const COLOR_OPTIONS: FarolColor[] = ["verde", "amarelo", "laranja", "vermelho"];

// -999 é o sentinela da engine para "sem piso real" na faixa mais baixa
// (band.min <= score <= band.max) — aqui é só exibição, o valor salvo não muda.
const OPEN_FLOOR_SENTINEL = -999;

function formatBandRange(min: number, max: number): string {
  return min <= OPEN_FLOOR_SENTINEL ? `≤ ${max}` : `${min}–${max}`;
}

export function BandsSection({
  readOnly,
  content,
  onContentChange,
  calibrators,
  onCalibratorChange,
  categories,
  onCategoryChange,
}: ContentProps & {
  calibrators: Calibrator[];
  onCalibratorChange: (index: number, patch: Partial<Calibrator>) => void;
  categories: MethodologyCategory[];
  onCategoryChange: (index: number, patch: Partial<MethodologyCategory>) => void;
}) {
  const weightSum = categories.reduce((total, category) => total + category.weight, 0);
  // Mesma tolerância da validação de publish no backend.
  const weightsOk = Math.abs(weightSum - 1) < 1e-6;

  return (
    <div className="methodology-section">
      <span className="kpi-label">Régua de faixas</span>
      <div className="farol-ruler">
        {calibrators.map((calibrator) => (
          <div key={calibrator.key} style={{ background: COLOR_HEX[calibrator.color] }}>
            {calibrator.label} ({formatBandRange(calibrator.min, calibrator.max)})
          </div>
        ))}
      </div>
      {readOnly
        ? null
        : calibrators.map((calibrator, index) => (
            <div className="form-row" key={calibrator.key}>
              <div className="form-field">
                <label>Cor</label>
                <select
                  aria-label={`Cor da faixa ${calibrator.label}`}
                  value={calibrator.color}
                  onChange={(e) => onCalibratorChange(index, { color: e.target.value as FarolColor })}
                >
                  {COLOR_OPTIONS.map((color) => (
                    <option key={color} value={color}>
                      {color}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label>Nome da faixa</label>
                <input
                  value={calibrator.label}
                  onChange={(e) => onCalibratorChange(index, { label: e.target.value })}
                />
              </div>
              <div className="form-field">
                <label>De</label>
                <input
                  type="number"
                  step="0.1"
                  aria-label={`Mínimo da faixa ${calibrator.label}`}
                  value={calibrator.min}
                  onChange={(e) => onCalibratorChange(index, { min: Number(e.target.value) })}
                />
              </div>
              <div className="form-field">
                <label>Até</label>
                <input
                  type="number"
                  step="0.1"
                  aria-label={`Máximo da faixa ${calibrator.label}`}
                  value={calibrator.max}
                  onChange={(e) => onCalibratorChange(index, { max: Number(e.target.value) })}
                />
              </div>
            </div>
          ))}

      <span className="kpi-label">Pesos na nota geral</span>
      <p className="methodology-hint">
        A nota geral é a soma ponderada das notas por critério. Os pesos precisam somar 100%.
      </p>
      {categories.map((category, index) => (
        <div className="form-field methodology-weight-row" key={category.key}>
          <label>{category.label}</label>
          {readOnly ? (
            <span className="methodology-readonly">{(category.weight * 100).toFixed(0)}%</span>
          ) : (
            <input
              type="number"
              step="1"
              min="0"
              max="100"
              aria-label={`Peso de ${category.label}`}
              value={Math.round(category.weight * 100)}
              onChange={(e) => onCategoryChange(index, { weight: Number(e.target.value) / 100 })}
            />
          )}
        </div>
      ))}
      <p className={weightsOk ? "methodology-hint" : "error-text"}>
        Soma: {(weightSum * 100).toFixed(0)}%
        {weightsOk ? "" : " — precisa ser 100% para publicar."}
      </p>

      <TextAreaField
        label="Regra da nota final"
        value={content.final_score_rule ?? ""}
        readOnly={readOnly}
        rows={6}
        hint="Os pesos acima são anexados automaticamente a este texto no prompt."
        onChange={(final_score_rule) => onContentChange({ final_score_rule })}
      />
    </div>
  );
}

// --- 5. saída e relatórios ---------------------------------------------------------

export function OutputSection({ readOnly, content, onContentChange }: ContentProps) {
  const taxonomy = content.development_taxonomy;
  const result = content.result_potential;
  const commercial = content.pb_commercial_potential;

  return (
    <div className="methodology-section">
      {result ? (
        <TextAreaField
          label="Potencial de geração de resultado da reunião"
          value={result.description}
          readOnly={readOnly}
          rows={5}
          hint={`Níveis: ${result.levels.join(", ")}`}
          onChange={(description) => onContentChange({ result_potential: { ...result, description } })}
        />
      ) : null}
      {commercial ? (
        <>
          <TextAreaField
            label="Potencial comercial do PB"
            value={commercial.description}
            readOnly={readOnly}
            rows={5}
            hint={`Níveis: ${commercial.levels.join(", ")}`}
            onChange={(description) =>
              onContentChange({ pb_commercial_potential: { ...commercial, description } })
            }
          />
          <TextAreaField
            label="Aviso sobre o potencial comercial"
            value={commercial.warning}
            readOnly={readOnly}
            rows={4}
            onChange={(warning) =>
              onContentChange({ pb_commercial_potential: { ...commercial, warning } })
            }
          />
        </>
      ) : null}
      {taxonomy ? (
        <Collapsible title="Taxonomia de desenvolvimento">
          <TextField
            label="Pontos preservados"
            value={taxonomy.pontos_preservados}
            readOnly={readOnly}
            onChange={(v) => onContentChange({ development_taxonomy: { ...taxonomy, pontos_preservados: v } })}
          />
          <TextField
            label="Riscos"
            value={taxonomy.riscos}
            readOnly={readOnly}
            onChange={(riscos) => onContentChange({ development_taxonomy: { ...taxonomy, riscos } })}
          />
          <TextField
            label="Oportunidades perdidas"
            value={taxonomy.oportunidades_perdidas}
            readOnly={readOnly}
            onChange={(v) =>
              onContentChange({ development_taxonomy: { ...taxonomy, oportunidades_perdidas: v } })
            }
          />
        </Collapsible>
      ) : null}
      <TextAreaField
        label="Regra das perguntas sugeridas"
        value={content.suggested_questions_rule ?? ""}
        readOnly={readOnly}
        rows={4}
        onChange={(suggested_questions_rule) => onContentChange({ suggested_questions_rule })}
      />
      <StringListField
        label="Exemplos de perguntas"
        values={content.suggested_questions_examples ?? []}
        readOnly={readOnly}
        addLabel="Adicionar pergunta"
        hint="Servem de espírito, não de script — a IA é instruída a adaptar ao caso."
        onChange={(suggested_questions_examples) => onContentChange({ suggested_questions_examples })}
      />
      <TextAreaField
        label="Regra da recomendação executiva"
        value={content.executive_recommendation_rule ?? ""}
        readOnly={readOnly}
        rows={4}
        onChange={(executive_recommendation_rule) => onContentChange({ executive_recommendation_rule })}
      />
      <TextAreaField
        label="Regra das notas de T&D"
        value={content.training_notes_rule ?? ""}
        readOnly={readOnly}
        rows={4}
        onChange={(training_notes_rule) => onContentChange({ training_notes_rule })}
      />
    </div>
  );
}

// --- 6. prévia do prompt -----------------------------------------------------------

export function PromptPreviewSection({
  preview,
  isLoading,
  isError,
}: {
  preview: MethodologyPromptPreview | undefined;
  isLoading: boolean;
  isError: boolean;
}) {
  if (isLoading) return <p className="page-subtitle">Compilando o prompt…</p>;
  if (isError || !preview) {
    return (
      <p className="page-subtitle">
        Não foi possível compilar o prompt desta versão. Isso acontece quando algum bloco global
        obrigatório está faltando.
      </p>
    );
  }

  return (
    <div className="methodology-section">
      <p className="methodology-hint">
        É exatamente o texto que a engine recebe. O preâmbulo vai nas 7 etapas da análise; o bloco
        de critérios, só na etapa que atribui as notas.
      </p>
      <span className="kpi-label">Preâmbulo</span>
      <pre className="methodology-prompt">{preview.system_preamble}</pre>
      <span className="kpi-label">Critérios</span>
      <pre className="methodology-prompt">{preview.criteria_block}</pre>
    </div>
  );
}
