/**
 * Os 6 critérios: definição refinada, peso, régua de âncoras, exemplos ancorados,
 * rubrica de subdimensões e regras de elegibilidade.
 *
 * É a aba que materializa a mudança da V2.1 — até aqui o admin editava duas linhas por
 * critério e a IA decidia a nota sozinha. Tudo que é editado nesta tela é compilado por
 * engine_integration/calibration_builder.py para dentro do system prompt.
 */
import { ANCHOR_LEVELS, TRANSVERSAL_SCOPE_KEY } from "../../types/methodology";
import type {
  MethodologyAnchor,
  MethodologyAnchorExample,
  MethodologyCategory,
  MethodologyEligibilityRule,
  MethodologySubdimension,
} from "../../types/methodology";
import Collapsible from "../ui/Collapsible";
import Icon from "../ui/Icon";
import { TextAreaField, TextField } from "./fields";

export interface CriteriaSectionProps {
  readOnly: boolean;
  categories: MethodologyCategory[];
  anchors: MethodologyAnchor[];
  examples: MethodologyAnchorExample[];
  subdimensions: MethodologySubdimension[];
  eligibilityRules: MethodologyEligibilityRule[];
  onCategoryChange: (index: number, patch: Partial<MethodologyCategory>) => void;
  onAnchorsChange: (anchors: MethodologyAnchor[]) => void;
  onExamplesChange: (examples: MethodologyAnchorExample[]) => void;
  onSubdimensionsChange: (subdimensions: MethodologySubdimension[]) => void;
  onEligibilityChange: (rules: MethodologyEligibilityRule[]) => void;
}

function formatWeight(weight: number): string {
  return `${(weight * 100).toFixed(0)}%`;
}

export default function CriteriaSection({
  readOnly,
  categories,
  anchors,
  examples,
  subdimensions,
  eligibilityRules,
  onCategoryChange,
  onAnchorsChange,
  onExamplesChange,
  onSubdimensionsChange,
  onEligibilityChange,
}: CriteriaSectionProps) {
  if (categories.length === 0) {
    return <p className="page-subtitle">Esta versão ainda não tem critérios cadastrados.</p>;
  }

  return (
    <div className="methodology-section">
      {categories.map((category, index) => (
        <Collapsible
          key={category.key}
          title={category.label}
          badge={formatWeight(category.weight)}
          defaultOpen={index === 0}
        >
          <TextField
            label="Nome exibido"
            value={category.label}
            readOnly={readOnly}
            onChange={(label) => onCategoryChange(index, { label })}
          />
          <TextAreaField
            label="O que avalia"
            value={category.description}
            readOnly={readOnly}
            rows={3}
            onChange={(description) => onCategoryChange(index, { description })}
          />
          <TextField
            label="Pergunta central"
            value={category.central_question ?? ""}
            readOnly={readOnly}
            hint="A pergunta que a IA deve responder ao avaliar este critério."
            onChange={(value) => onCategoryChange(index, { central_question: value || null })}
          />
          <TextAreaField
            label="NÃO significa"
            value={category.what_it_is_not ?? ""}
            readOnly={readOnly}
            rows={2}
            hint="A anti-definição. É o que impede a IA de confundir cordialidade com conexão."
            onChange={(value) => onCategoryChange(index, { what_it_is_not: value || null })}
          />
          <TextAreaField
            label="Evidências positivas"
            value={category.positive_evidence ?? ""}
            readOnly={readOnly}
            rows={2}
            onChange={(value) => onCategoryChange(index, { positive_evidence: value || null })}
          />
          <TextAreaField
            label="Evidências negativas"
            value={category.negative_evidence ?? ""}
            readOnly={readOnly}
            rows={2}
            onChange={(value) => onCategoryChange(index, { negative_evidence: value || null })}
          />
          <TextAreaField
            label="Interação com outros critérios"
            value={category.cross_impact_text ?? ""}
            readOnly={readOnly}
            rows={2}
            onChange={(value) => onCategoryChange(index, { cross_impact_text: value || null })}
          />

          <AnchorEditor
            readOnly={readOnly}
            scopeKey={category.key}
            anchors={anchors}
            onChange={onAnchorsChange}
          />
          <ExampleEditor
            readOnly={readOnly}
            criterionKey={category.key}
            examples={examples}
            onChange={onExamplesChange}
          />
          <SubdimensionEditor
            readOnly={readOnly}
            criterionKey={category.key}
            subdimensions={subdimensions}
            onChange={onSubdimensionsChange}
          />
          <EligibilityEditor
            readOnly={readOnly}
            scopeKey={category.key}
            rules={eligibilityRules}
            onChange={onEligibilityChange}
          />
        </Collapsible>
      ))}

      <Collapsible title="Regras transversais de elegibilidade">
        <p className="methodology-hint">
          Valem para todos os critérios — entram no bloco de cada um deles no prompt.
        </p>
        <EligibilityEditor
          readOnly={readOnly}
          scopeKey={TRANSVERSAL_SCOPE_KEY}
          rules={eligibilityRules}
          onChange={onEligibilityChange}
        />
      </Collapsible>
    </div>
  );
}

// --- âncoras -----------------------------------------------------------------------

export function AnchorEditor({
  readOnly,
  scopeKey,
  anchors,
  onChange,
  title = "Âncoras observáveis (0–10)",
}: {
  readOnly: boolean;
  scopeKey: string;
  anchors: MethodologyAnchor[];
  onChange: (anchors: MethodologyAnchor[]) => void;
  title?: string;
}) {
  function setDescriptor(level: number, descriptor: string) {
    const existing = anchors.find((a) => a.scope_key === scopeKey && a.level === level);
    if (existing) {
      onChange(
        anchors.map((a) => (a.scope_key === scopeKey && a.level === level ? { ...a, descriptor } : a)),
      );
      return;
    }
    onChange([
      ...anchors,
      {
        scope: scopeKey.startsWith("pilar_") ? "PILLAR" : "CRITERION",
        scope_key: scopeKey,
        level,
        descriptor,
        order_index: anchors.length,
      },
    ]);
  }

  return (
    <fieldset className="methodology-fieldset">
      <legend>{title}</legend>
      <p className="methodology-hint">
        A régua que impede a nota de ser arbitrada. Publicar exige os cinco níveis preenchidos.
      </p>
      {ANCHOR_LEVELS.map((level) => {
        const anchor = anchors.find((a) => a.scope_key === scopeKey && a.level === level);
        return (
          <div className="methodology-anchor-row" key={level}>
            <span className="methodology-anchor-level">{level}</span>
            {readOnly ? (
              <p className="methodology-readonly">{anchor?.descriptor || <em>sem âncora</em>}</p>
            ) : (
              <textarea
                rows={2}
                aria-label={`Âncora de nível ${level}`}
                value={anchor?.descriptor ?? ""}
                onChange={(e) => setDescriptor(level, e.target.value)}
              />
            )}
          </div>
        );
      })}
    </fieldset>
  );
}

// --- exemplos ancorados ------------------------------------------------------------

function ExampleEditor({
  readOnly,
  criterionKey,
  examples,
  onChange,
}: {
  readOnly: boolean;
  criterionKey: MethodologyCategory["key"];
  examples: MethodologyAnchorExample[];
  onChange: (examples: MethodologyAnchorExample[]) => void;
}) {
  const mine = examples.filter((e) => e.criterion_key === criterionKey);

  function patch(example: MethodologyAnchorExample, changes: Partial<MethodologyAnchorExample>) {
    onChange(examples.map((e) => (e === example ? { ...e, ...changes } : e)));
  }

  return (
    <fieldset className="methodology-fieldset">
      <legend>Exemplos ancorados</legend>
      <p className="methodology-hint">
        A fala concreta de cada nível. É o que permite à IA inferir a valoração em vez de supor.
      </p>
      {mine.map((example) => (
        <div className="methodology-example" key={example.order_index}>
          <div className="methodology-example-head">
            <span className="methodology-anchor-level">{example.level}</span>
            {readOnly ? null : (
              <>
                <select
                  aria-label="Nível do exemplo"
                  value={example.level}
                  onChange={(e) => patch(example, { level: Number(e.target.value) })}
                >
                  {ANCHOR_LEVELS.map((level) => (
                    <option key={level} value={level}>
                      Nota {level}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="methodology-icon-button"
                  aria-label={`Remover exemplo de nota ${example.level}`}
                  onClick={() => onChange(examples.filter((e) => e !== example))}
                >
                  <Icon name="close" size={18} />
                </button>
              </>
            )}
          </div>
          <TextField
            label="Cenário (opcional)"
            value={example.scenario ?? ""}
            readOnly={readOnly}
            onChange={(value) => patch(example, { scenario: value || null })}
          />
          <TextField
            label="Fala (opcional)"
            value={example.quote ?? ""}
            readOnly={readOnly}
            onChange={(value) => patch(example, { quote: value || null })}
          />
          <TextAreaField
            label="Por quê"
            value={example.rationale}
            readOnly={readOnly}
            rows={2}
            onChange={(rationale) => patch(example, { rationale })}
          />
        </div>
      ))}
      {readOnly ? null : (
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() =>
            onChange([
              ...examples,
              {
                criterion_key: criterionKey,
                level: 8,
                scenario: null,
                quote: null,
                rationale: "",
                order_index: examples.length,
              },
            ])
          }
        >
          <Icon name="add" size={18} /> Adicionar exemplo
        </button>
      )}
    </fieldset>
  );
}

// --- subdimensões ------------------------------------------------------------------

function SubdimensionEditor({
  readOnly,
  criterionKey,
  subdimensions,
  onChange,
}: {
  readOnly: boolean;
  criterionKey: MethodologyCategory["key"];
  subdimensions: MethodologySubdimension[];
  onChange: (subdimensions: MethodologySubdimension[]) => void;
}) {
  const mine = subdimensions.filter((s) => s.criterion_key === criterionKey);

  function patch(sub: MethodologySubdimension, changes: Partial<MethodologySubdimension>) {
    onChange(subdimensions.map((s) => (s === sub ? { ...s, ...changes } : s)));
  }

  return (
    <fieldset className="methodology-fieldset">
      <legend>Rubrica de subdimensões (0–4)</legend>
      <p className="methodology-hint">
        Instrumento de auditoria dentro da âncora — a nota nunca sai da média das subdimensões.
      </p>
      {mine.map((sub) => (
        <div className="methodology-subdimension" key={sub.order_index}>
          <div className="methodology-example-head">
            {readOnly ? (
              <strong>{sub.name}</strong>
            ) : (
              <>
                <input
                  aria-label="Nome da subdimensão"
                  value={sub.name}
                  onChange={(e) => patch(sub, { name: e.target.value })}
                />
                <button
                  type="button"
                  className="methodology-icon-button"
                  aria-label={`Remover subdimensão ${sub.name}`}
                  onClick={() => onChange(subdimensions.filter((s) => s !== sub))}
                >
                  <Icon name="close" size={18} />
                </button>
              </>
            )}
          </div>
          {sub.levels.map((level, levelIndex) => (
            // A posição é a identidade: o nível é o índice, e o texto muda a cada tecla.
            // eslint-disable-next-line react/no-array-index-key
            <div className="methodology-anchor-row" key={levelIndex}>
              <span className="methodology-anchor-level">{levelIndex}</span>
              {readOnly ? (
                <p className="methodology-readonly">{level}</p>
              ) : (
                <input
                  aria-label={`${sub.name} nível ${levelIndex}`}
                  value={level}
                  onChange={(e) =>
                    patch(sub, {
                      levels: sub.levels.map((l, i) => (i === levelIndex ? e.target.value : l)),
                    })
                  }
                />
              )}
            </div>
          ))}
        </div>
      ))}
      {readOnly ? null : (
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() =>
            onChange([
              ...subdimensions,
              {
                criterion_key: criterionKey,
                name: "Nova subdimensão",
                levels: ["", "", "", "", ""],
                order_index: subdimensions.length,
              },
            ])
          }
        >
          <Icon name="add" size={18} /> Adicionar subdimensão
        </button>
      )}
    </fieldset>
  );
}

// --- elegibilidade de faixa --------------------------------------------------------

function EligibilityEditor({
  readOnly,
  scopeKey,
  rules,
  onChange,
}: {
  readOnly: boolean;
  scopeKey: string;
  rules: MethodologyEligibilityRule[];
  onChange: (rules: MethodologyEligibilityRule[]) => void;
}) {
  const mine = rules.filter((r) => r.scope_key === scopeKey);

  function patch(rule: MethodologyEligibilityRule, changes: Partial<MethodologyEligibilityRule>) {
    onChange(rules.map((r) => (r === rule ? { ...r, ...changes } : r)));
  }

  return (
    <fieldset className="methodology-fieldset">
      <legend>Elegibilidade de faixa</legend>
      <p className="methodology-hint">
        Condições que impedem determinadas notas. Boa evidência em outro ponto não as neutraliza.
      </p>
      {mine.map((rule) => (
        <div className="methodology-rule" key={rule.order_index}>
          {readOnly ? (
            <p className="methodology-readonly">
              {rule.condition}
              {rule.effect === "CAP" ? ` → nota no máximo ${rule.max_score}` : ""}
            </p>
          ) : (
            <>
              <input
                aria-label="Condição"
                value={rule.condition}
                onChange={(e) => patch(rule, { condition: e.target.value })}
              />
              <select
                aria-label="Efeito"
                value={rule.effect}
                onChange={(e) =>
                  patch(rule, {
                    effect: e.target.value as MethodologyEligibilityRule["effect"],
                    max_score: e.target.value === "CAP" ? (rule.max_score ?? 7.9) : null,
                  })
                }
              >
                <option value="CAP">Limita a nota a</option>
                <option value="NOTE">Observação (sem teto)</option>
              </select>
              {rule.effect === "CAP" ? (
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="10"
                  aria-label="Nota máxima"
                  value={rule.max_score ?? 0}
                  onChange={(e) => patch(rule, { max_score: Number(e.target.value) })}
                />
              ) : null}
              <button
                type="button"
                className="methodology-icon-button"
                aria-label={`Remover regra "${rule.condition}"`}
                onClick={() => onChange(rules.filter((r) => r !== rule))}
              >
                <Icon name="close" size={18} />
              </button>
            </>
          )}
        </div>
      ))}
      {readOnly ? null : (
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() =>
            onChange([
              ...rules,
              {
                scope_key: scopeKey,
                condition: "",
                effect: "CAP",
                max_score: 7.9,
                order_index: rules.length,
              },
            ])
          }
        >
          <Icon name="add" size={18} /> Adicionar regra
        </button>
      )}
    </fieldset>
  );
}
