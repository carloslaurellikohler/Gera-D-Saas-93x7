import { useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import { useConfirm } from "../../context/ConfirmContext";
import { useAiCostConfig } from "../../hooks/useAiCostConfig";
import { useAiModelPrices } from "../../hooks/useAiModelPrices";
import { useRecalculateAiModelPrice } from "../../hooks/useRecalculateAiModelPrice";
import { useUnpricedAiModels } from "../../hooks/useUnpricedAiModels";
import { useUpdateAiCostConfig } from "../../hooks/useUpdateAiCostConfig";
import { formatDate, formatDateTime } from "../../lib/format";
import type { AiCostOperation, AiModelPrice } from "../../types/aiCost";
import AiModelPriceForm from "../forms/AiModelPriceForm";
import EmptyState from "../ui/EmptyState";
import ErrorBanner from "../ui/ErrorBanner";
import Icon from "../ui/Icon";
import Modal from "../ui/Modal";

const PRICE_COLUMNS = "minmax(0, 1.2fr) 150px 120px 100px 100px 100px 110px 120px";

function priceCell(value: number | null): string {
  return value === null ? "—" : value.toLocaleString("pt-BR", { maximumFractionDigits: 6 });
}

export default function CostSettingsTab() {
  const prices = useAiModelPrices();
  const unpriced = useUnpricedAiModels();
  const config = useAiCostConfig();
  const updateConfig = useUpdateAiCostConfig();
  const recalculate = useRecalculateAiModelPrice();
  const confirm = useConfirm();

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<AiModelPrice | undefined>(undefined);
  const [prefill, setPrefill] = useState<{ model: string; operation: AiCostOperation } | undefined>(
    undefined,
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const [threshold, setThreshold] = useState("80");
  const [budget, setBudget] = useState("");
  const [rate, setRate] = useState("");

  // Espelha a configuração carregada em estado local — mesmo padrão de CalibrationPage.
  useEffect(() => {
    if (!config.data) return;
    setThreshold(String(config.data.warn_threshold_pct));
    setBudget(
      config.data.current_month_budget_usd === null
        ? ""
        : String(config.data.current_month_budget_usd),
    );
    setRate(config.data.usd_to_brl_rate === null ? "" : String(config.data.usd_to_brl_rate));
  }, [config.data]);

  const handleSaveConfig = async () => {
    setActionError(null);
    setFeedback(null);
    try {
      await updateConfig.mutateAsync({
        warn_threshold_pct: Number(threshold),
        usd_to_brl_rate: rate.trim() ? Number(rate) : null,
        monthly_budget_usd: budget.trim() ? Number(budget) : null,
      });
      setFeedback("Configuração salva.");
    } catch (err) {
      setActionError(
        err instanceof ApiError ? err.message : "Erro ao salvar a configuração financeira.",
      );
    }
  };

  const handleRecalculate = async (price: AiModelPrice) => {
    const confirmed = await confirm({
      title: "Recalcular histórico?",
      description:
        `Isso reescreve o custo já gravado das chamadas de ${price.model} ` +
        `(${price.operation}) a partir de ${formatDate(price.valid_from)}. ` +
        "O custo de cada chamada é congelado na gravação justamente para que meses " +
        "fechados não mudem sozinhos — esta ação é a exceção, e é irreversível.",
      confirmLabel: "Recalcular",
      tone: "danger",
    });
    if (!confirmed) return;

    setActionError(null);
    setFeedback(null);
    try {
      const result = await recalculate.mutateAsync(price.id);
      setFeedback(
        result.updated === 0
          ? "Nenhuma chamada precisou de ajuste."
          : `${result.updated} ${result.updated === 1 ? "chamada recalculada" : "chamadas recalculadas"}.`,
      );
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Erro ao recalcular o histórico.");
    }
  };

  return (
    <div style={{ marginTop: 20 }}>
      {actionError && <ErrorBanner>{actionError}</ErrorBanner>}
      {feedback && (
        <div className="info-banner" style={{ marginBottom: 16 }}>
          <Icon name="check_circle" size={20} />
          <span>{feedback}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 4 }}>Orçamento e exibição</h3>
        <p className="page-subtitle" style={{ marginBottom: 16 }}>
          A meta vale para{" "}
          {config.data ? formatDate(config.data.current_month) : "o mês corrente"} e serve apenas
          para acompanhamento: <strong>nenhuma análise é bloqueada</strong> ao estourá-la.
        </p>

        <div className="form-row">
          <div className="form-field">
            <label htmlFor="cost-budget">Meta do mês (US$)</label>
            <input
              id="cost-budget"
              type="number"
              min="0"
              step="1"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="em branco = sem meta"
            />
          </div>
          <div className="form-field">
            <label htmlFor="cost-threshold">Alertar a partir de (% da meta)</label>
            <input
              id="cost-threshold"
              type="number"
              min="1"
              max="100"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
            />
          </div>
        </div>

        <div className="form-field">
          <label htmlFor="cost-rate">Cotação do dólar (R$ por US$)</label>
          <input
            id="cost-rate"
            type="number"
            min="0"
            step="0.0001"
            value={rate}
            onChange={(e) => setRate(e.target.value)}
            placeholder="ex.: 5.42"
          />
          <span className="page-subtitle" style={{ fontSize: 12 }}>
            Usada só para exibir o equivalente em reais ao lado do valor em dólar. Nenhum valor
            em BRL é armazenado.
            {config.data?.usd_to_brl_rate_updated_at &&
              ` Última atualização: ${formatDateTime(config.data.usd_to_brl_rate_updated_at)}.`}
          </span>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSaveConfig}
            disabled={updateConfig.isPending}
          >
            {updateConfig.isPending ? "Salvando..." : "Salvar configuração"}
          </button>
        </div>
      </div>

      {/* Fecha o laço entre o que roda e o que está cadastrado. O nome aqui é a string
          exata que a API reportou — cadastrar o nome do .env pode não casar, porque a
          OpenAI costuma responder com snapshot datado (ex.: gpt-4.1-2025-04-14). */}
      {unpriced.data && unpriced.data.length > 0 && (
        <div
          className="card"
          style={{ marginBottom: 16, borderLeft: "3px solid var(--content-alert)" }}
        >
          <h3 style={{ marginBottom: 4 }}>Modelos em uso sem preço cadastrado</h3>
          <p className="page-subtitle" style={{ marginBottom: 14 }}>
            Estas chamadas já aconteceram mas não entram no total. O nome abaixo é o que a
            API de fato reportou — cadastre exatamente ele.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {unpriced.data.map((item) => (
              <div
                key={`${item.model}-${item.operation}`}
                style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 13 }}
              >
                <code
                  style={{
                    background: "var(--background-secondary)",
                    padding: "2px 8px",
                    borderRadius: "var(--corner-extra-small)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {item.model}
                </code>
                <span style={{ color: "var(--content-secondary)" }}>{item.operation}</span>
                <span style={{ color: "var(--content-secondary)", flex: 1 }}>
                  {item.events} {item.events === 1 ? "chamada" : "chamadas"} · última em{" "}
                  {formatDate(item.last_seen)}
                </span>
                <button
                  type="button"
                  className="btn btn-secondary"
                  // Rótulo distinto por linha: com vários pendentes, "Cadastrar preço"
                  // sozinho não diz a qual modelo se refere.
                  aria-label={`Cadastrar preço de ${item.model}`}
                  style={{ height: 32, padding: "0 14px" }}
                  onClick={() => {
                    setEditing(undefined);
                    setPrefill({ model: item.model, operation: item.operation });
                    setFormOpen(true);
                  }}
                >
                  Cadastrar preço
                </button>
              </div>
            ))}
          </div>
          <p className="page-subtitle" style={{ marginTop: 14, fontSize: 12 }}>
            Cadastrar o preço passa a custear as chamadas <strong>novas</strong>. Para
            reprecificar as que já aconteceram, use "recalcular histórico" na linha do preço.
          </p>
        </div>
      )}

      <div className="page-header" style={{ marginBottom: 0 }}>
        <div className="page-title-group">
          <h3>Preços por modelo</h3>
          <span className="page-subtitle">
            Versionados por vigência: cadastrar um preço novo não reescreve o custo já apurado.
          </span>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => {
            setEditing(undefined);
            setPrefill(undefined);
            setFormOpen(true);
          }}
        >
          Cadastrar preço
        </button>
      </div>

      {prices.isLoading && <p className="page-subtitle">Carregando...</p>}
      {prices.isError && <p className="error-text">Não foi possível carregar os preços.</p>}

      {prices.data && prices.data.length === 0 && (
        <EmptyState
          icon="price_change"
          title="Nenhum preço cadastrado"
          description="Sem preço, as chamadas ficam registradas mas sem custo apurado, e o total aparece subestimado."
        />
      )}

      {prices.data && prices.data.length > 0 && (
        <div className="data-table" style={{ marginTop: 16 }}>
          <div
            className="data-table-row data-table-head"
            style={{ gridTemplateColumns: PRICE_COLUMNS }}
          >
            <span>Modelo</span>
            <span>Operação</span>
            <span>Vigente desde</span>
            <span style={{ textAlign: "right" }}>Entrada</span>
            <span style={{ textAlign: "right" }}>Cache</span>
            <span style={{ textAlign: "right" }}>Saída</span>
            <span style={{ textAlign: "right" }}>US$/min</span>
            <span style={{ textAlign: "right" }}>Ações</span>
          </div>
          {prices.data.map((price) => (
            <div
              key={price.id}
              className="data-table-row"
              style={{ gridTemplateColumns: PRICE_COLUMNS }}
            >
              <span>
                {price.model}
                {price.is_current && (
                  <span className="pill" style={{ marginLeft: 6, fontSize: 11, padding: "1px 6px" }}>
                    vigente
                  </span>
                )}
                {price.is_placeholder && (
                  <span
                    className="pill"
                    style={{
                      marginLeft: 6,
                      fontSize: 11,
                      padding: "1px 6px",
                      background: "var(--background-alert-n2)",
                    }}
                    title="Valor estimado, não confirmado"
                  >
                    estimado
                  </span>
                )}
              </span>
              <span style={{ fontSize: 13 }}>{price.operation}</span>
              <span style={{ fontSize: 13 }}>{formatDate(price.valid_from)}</span>
              <span style={{ textAlign: "right", fontSize: 13 }}>
                {priceCell(price.input_usd_per_mtok)}
              </span>
              <span style={{ textAlign: "right", fontSize: 13 }}>
                {priceCell(price.cached_input_usd_per_mtok)}
              </span>
              <span style={{ textAlign: "right", fontSize: 13 }}>
                {priceCell(price.output_usd_per_mtok)}
              </span>
              <span style={{ textAlign: "right", fontSize: 13 }}>
                {priceCell(price.usd_per_minute)}
              </span>
              <span style={{ textAlign: "right", display: "flex", gap: 6, justifyContent: "flex-end" }}>
                <button
                  type="button"
                  aria-label={`Editar preço de ${price.model}`}
                  onClick={() => {
                    setEditing(price);
                    setPrefill(undefined);
                    setFormOpen(true);
                  }}
                  style={{ background: "none", border: "none", cursor: "pointer", padding: 2 }}
                >
                  <Icon name="edit" size={18} />
                </button>
                <button
                  type="button"
                  aria-label={`Recalcular histórico de ${price.model}`}
                  onClick={() => handleRecalculate(price)}
                  disabled={recalculate.isPending}
                  style={{ background: "none", border: "none", cursor: "pointer", padding: 2 }}
                >
                  <Icon name="refresh" size={18} />
                </button>
              </span>
            </div>
          ))}
        </div>
      )}

      <Modal
        open={formOpen}
        title={editing ? "Editar preço" : prefill ? `Cadastrar preço de ${prefill.model}` : "Cadastrar preço"}
        onClose={() => setFormOpen(false)}
      >
        <AiModelPriceForm
          editing={editing}
          prefill={prefill}
          onDone={() => setFormOpen(false)}
        />
      </Modal>
    </div>
  );
}
