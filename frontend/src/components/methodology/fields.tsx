/**
 * Campos de formulário da tela de metodologia.
 *
 * Todos recebem `readOnly`: a tela mostra exatamente os mesmos blocos para uma versão
 * publicada ou encerrada, só que sem edição — é assim que dá para auditar qual régua
 * gerou uma análise antiga.
 */
import Icon from "../ui/Icon";

interface TextFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  readOnly: boolean;
  hint?: string;
  placeholder?: string;
}

export function TextField({ label, value, onChange, readOnly, hint, placeholder }: TextFieldProps) {
  return (
    <div className="form-field">
      <label>{label}</label>
      {readOnly ? (
        <p className="methodology-readonly">{value || <em>não preenchido</em>}</p>
      ) : (
        <input value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
      )}
      {hint ? <span className="methodology-hint">{hint}</span> : null}
    </div>
  );
}

interface TextAreaFieldProps extends TextFieldProps {
  rows?: number;
}

export function TextAreaField({
  label,
  value,
  onChange,
  readOnly,
  hint,
  placeholder,
  rows = 4,
}: TextAreaFieldProps) {
  return (
    <div className="form-field">
      <label>{label}</label>
      {readOnly ? (
        <p className="methodology-readonly methodology-prewrap">{value || <em>não preenchido</em>}</p>
      ) : (
        <textarea
          rows={rows}
          value={value}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
      {hint ? <span className="methodology-hint">{hint}</span> : null}
    </div>
  );
}

interface StringListFieldProps {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
  readOnly: boolean;
  hint?: string;
  addLabel: string;
}

/** Lista de linhas de texto (comportamentos proibidos, exemplos de perguntas, níveis). */
export function StringListField({
  label,
  values,
  onChange,
  readOnly,
  hint,
  addLabel,
}: StringListFieldProps) {
  function update(index: number, value: string) {
    onChange(values.map((item, i) => (i === index ? value : item)));
  }

  return (
    <div className="form-field">
      <label>{label}</label>
      {hint ? <span className="methodology-hint">{hint}</span> : null}
      <ul className="methodology-string-list">
        {values.map((value, index) => (
          // A posição é a identidade da linha: o texto pode repetir e muda a cada tecla.
          // eslint-disable-next-line react/no-array-index-key
          <li key={index}>
            {readOnly ? (
              <span className="methodology-readonly">{value}</span>
            ) : (
              <>
                <input value={value} onChange={(e) => update(index, e.target.value)} />
                <button
                  type="button"
                  className="methodology-icon-button"
                  aria-label={`Remover "${value}"`}
                  onClick={() => onChange(values.filter((_, i) => i !== index))}
                >
                  <Icon name="close" size={18} />
                </button>
              </>
            )}
          </li>
        ))}
      </ul>
      {readOnly ? null : (
        <button type="button" className="btn btn-secondary" onClick={() => onChange([...values, ""])}>
          <Icon name="add" size={18} /> {addLabel}
        </button>
      )}
    </div>
  );
}
