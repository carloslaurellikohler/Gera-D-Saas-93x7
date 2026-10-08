import { useState } from "react";
import { ApiError } from "../../api/client";
import { useSaveAiModelPrice } from "../../hooks/useSaveAiModelPrice";
import type { AiCostOperation, AiModelPrice, AiModelPricePayload } from "../../types/aiCost";
import ErrorBanner from "../ui/ErrorBanner";

const OPERATION_LABELS: Record<AiCostOperation, string> = {
  CHAT: "Chat (análise e assistente)",
  TRANSCRIPTION: "Transcrição de áudio",
  EMBEDDING: "Embeddings",
};

function toInput(value: number | null | undefined): string {
  return value === null || value === undefined ? "" : String(value);
}

function toNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

export default function AiModelPriceForm({
  onDone,
  editing,
}: {
  onDone: () => void;
  editing?: AiModelPrice;
}) {
  const savePrice = useSaveAiModelPrice();

  const [model, setModel] = useState(editing?.model ?? "");
  const [operation, setOperation] = useState<AiCostOperation>(editing?.operation ?? "CHAT");
  // Inicializador lazy: `new Date()` não deve rodar a cada render.
  const [validFrom, setValidFrom] = useState(
    () => editing?.valid_from ?? new Date().toISOString().slice(0, 10),
  );
  const [inputPrice, setInputPrice] = useState(toInput(editing?.input_usd_per_mtok));
  const [cachedPrice, setCachedPrice] = useState(toInput(editing?.cached_input_usd_per_mtok));
  const [outputPrice, setOutputPrice] = useState(toInput(editing?.output_usd_per_mtok));
  const [minutePrice, setMinutePrice] = useState(toInput(editing?.usd_per_minute));
  const [notes, setNotes] = useState(editing?.notes ?? "");
  const [error, setError] = useState<string | null>(null);

  const isTranscription = operation === "TRANSCRIPTION";
  const isChat = operation === "CHAT";

  const handleSubmit = async () => {
    setError(null);
    if (!model.trim()) {
      setError("Informe o nome do modelo, exatamente como a API da OpenAI o reporta.");
      return;
    }
    const payload: AiModelPricePayload = {
      model: model.trim(),
      operation,
      valid_from: validFrom,
      input_usd_per_mtok: isTranscription ? null : toNumber(inputPrice),
      cached_input_usd_per_mtok: isChat ? toNumber(cachedPrice) : null,
      output_usd_per_mtok: isChat ? toNumber(outputPrice) : null,
      usd_per_minute: isTranscription ? toNumber(minutePrice) : null,
      notes: notes.trim() || null,
    };
    try {
      await savePrice.mutateAsync({ id: editing?.id, payload });
      onDone();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : `Erro ao ${editing ? "salvar" : "cadastrar"} preço.`,
      );
    }
  };

  return (
    <div>
      {error && <ErrorBanner>{error}</ErrorBanner>}

      <p className="page-subtitle" style={{ marginTop: error ? 18 : 0, marginBottom: 16 }}>
        Os preços de token são por <strong>1 milhão de tokens</strong> — o mesmo formato da
        página de preços da OpenAI, para você digitar o número direto de lá.
      </p>

      <div className="form-field">
        <label htmlFor="price-model">Modelo</label>
        <input
          id="price-model"
          type="text"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="ex.: gpt-6-sol"
        />
      </div>

      <div className="form-row">
        <div className="form-field">
          <label htmlFor="price-operation">Operação</label>
          <select
            id="price-operation"
            value={operation}
            onChange={(e) => setOperation(e.target.value as AiCostOperation)}
          >
            {(Object.keys(OPERATION_LABELS) as AiCostOperation[]).map((key) => (
              <option key={key} value={key}>
                {OPERATION_LABELS[key]}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label htmlFor="price-valid-from">Vigente a partir de</label>
          <input
            id="price-valid-from"
            type="date"
            value={validFrom}
            onChange={(e) => setValidFrom(e.target.value)}
          />
        </div>
      </div>

      {isTranscription ? (
        <div className="form-field">
          <label htmlFor="price-minute">US$ por minuto de áudio</label>
          <input
            id="price-minute"
            type="number"
            step="0.000001"
            min="0"
            value={minutePrice}
            onChange={(e) => setMinutePrice(e.target.value)}
            placeholder="0.006"
          />
        </div>
      ) : (
        <>
          <div className="form-row">
            <div className="form-field">
              <label htmlFor="price-input">US$ por 1M tokens de entrada</label>
              <input
                id="price-input"
                type="number"
                step="0.000001"
                min="0"
                value={inputPrice}
                onChange={(e) => setInputPrice(e.target.value)}
              />
            </div>
            {isChat && (
              <div className="form-field">
                <label htmlFor="price-output">US$ por 1M tokens de saída</label>
                <input
                  id="price-output"
                  type="number"
                  step="0.000001"
                  min="0"
                  value={outputPrice}
                  onChange={(e) => setOutputPrice(e.target.value)}
                />
              </div>
            )}
          </div>
          {isChat && (
            <div className="form-field">
              <label htmlFor="price-cached">
                US$ por 1M tokens de entrada em cache (opcional)
              </label>
              <input
                id="price-cached"
                type="number"
                step="0.000001"
                min="0"
                value={cachedPrice}
                onChange={(e) => setCachedPrice(e.target.value)}
              />
              <span className="page-subtitle" style={{ fontSize: 12 }}>
                Em branco, o token em cache é cobrado como entrada cheia — erra para cima,
                nunca para baixo.
              </span>
            </div>
          )}
        </>
      )}

      <div className="form-field">
        <label htmlFor="price-notes">Observação (opcional)</label>
        <input
          id="price-notes"
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="ex.: conferido na página de preços em 08/10/2026"
        />
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
        <button type="button" className="btn btn-secondary" onClick={onDone}>
          Cancelar
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={savePrice.isPending}
        >
          {savePrice.isPending ? "Salvando..." : "Salvar preço"}
        </button>
      </div>
    </div>
  );
}
