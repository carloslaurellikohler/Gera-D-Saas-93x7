import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import ErrorBanner from "../components/ui/ErrorBanner";
import Icon from "../components/ui/Icon";
import { useConfirm } from "../context/ConfirmContext";
import { useRuntimeSettings } from "../hooks/useRuntimeSettings";
import { useTestAiModel } from "../hooks/useTestAiModel";
import { useUpdateRuntimeSettings } from "../hooks/useUpdateRuntimeSettings";
import { formatDateTime } from "../lib/format";

type ModelKind = "analysis" | "assistant";

interface TestResult {
  ok: boolean;
  message: string;
}

function isReasoningModel(model: string, prefixes: string[]): boolean {
  const lower = model.trim().toLowerCase();
  return prefixes.some((prefix) => lower.startsWith(prefix)) && !lower.includes("chat");
}

export default function SettingsPage() {
  const settings = useRuntimeSettings();
  const updateSettings = useUpdateRuntimeSettings();
  const testModel = useTestAiModel();
  const confirm = useConfirm();

  const [actionError, setActionError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  // Campos como string e conversão só no submit — mesmo padrão de CostSettingsTab.
  const [analysisLimit, setAnalysisLimit] = useState("");
  const [messageLimit, setMessageLimit] = useState("");
  const [analysisModel, setAnalysisModel] = useState("");
  const [analysisTemperature, setAnalysisTemperature] = useState("");
  const [assistantModel, setAssistantModel] = useState("");
  const [assistantTemperature, setAssistantTemperature] = useState("");

  const [testResults, setTestResults] = useState<Record<ModelKind, TestResult | null>>({
    analysis: null,
    assistant: null,
  });
  // Guarda o nome exato que passou no teste, para saber se o valor atual já foi validado.
  const [testedOk, setTestedOk] = useState<Record<ModelKind, string | null>>({
    analysis: null,
    assistant: null,
  });
  const [testingKind, setTestingKind] = useState<ModelKind | null>(null);

  // Espelha a configuração carregada em estado local — mesmo padrão de CalibrationPage.
  useEffect(() => {
    if (!settings.data) return;
    setAnalysisLimit(String(settings.data.daily_analysis_limit_per_owner));
    setMessageLimit(String(settings.data.assistant_daily_message_limit));
    setAnalysisModel(settings.data.analysis_model);
    setAnalysisTemperature(String(settings.data.analysis_temperature));
    setAssistantModel(settings.data.assistant_model);
    setAssistantTemperature(String(settings.data.assistant_temperature));
  }, [settings.data]);

  const prefixes = settings.data?.reasoning_model_prefixes ?? [];

  const modelFields: Record<ModelKind, { value: string; setValue: (v: string) => void }> = {
    analysis: { value: analysisModel, setValue: setAnalysisModel },
    assistant: { value: assistantModel, setValue: setAssistantModel },
  };

  const handleModelChange = (kind: ModelKind, value: string) => {
    modelFields[kind].setValue(value);
    // O resultado anterior deixa de valer assim que o nome muda.
    setTestResults((prev) => ({ ...prev, [kind]: null }));
  };

  const handleTestModel = async (kind: ModelKind) => {
    const model = modelFields[kind].value.trim();
    if (!model) return;

    setTestingKind(kind);
    setTestResults((prev) => ({ ...prev, [kind]: null }));
    try {
      const temperature = kind === "analysis" ? analysisTemperature : assistantTemperature;
      const result = await testModel.mutateAsync({
        model_name: model,
        temperature: temperature.trim() ? Number(temperature) : null,
      });
      setTestResults((prev) => ({ ...prev, [kind]: { ok: true, message: result.message } }));
      setTestedOk((prev) => ({ ...prev, [kind]: model }));
    } catch (err) {
      setTestResults((prev) => ({
        ...prev,
        [kind]: {
          ok: false,
          message: err instanceof ApiError ? err.message : "Não foi possível testar o modelo.",
        },
      }));
    } finally {
      setTestingKind(null);
    }
  };

  /** Modelos que mudaram e nunca passaram pelo teste — salvar um nome errado derruba toda
   *  análise ou resposta nova, então vale uma confirmação explícita. */
  const untestedChanges = (): string[] => {
    if (!settings.data) return [];
    const pending: string[] = [];
    const analysis = analysisModel.trim();
    const assistant = assistantModel.trim();
    if (analysis !== settings.data.analysis_model && testedOk.analysis !== analysis) {
      pending.push("da análise");
    }
    if (assistant !== settings.data.assistant_model && testedOk.assistant !== assistant) {
      pending.push("do assistente");
    }
    return pending;
  };

  const handleSave = async () => {
    setActionError(null);
    setFeedback(null);

    const pending = untestedChanges();
    if (pending.length > 0) {
      const confirmed = await confirm({
        title: "Salvar modelo não testado?",
        description:
          `O modelo ${pending.join(" e ")} foi alterado sem passar pelo teste. ` +
          "Se o nome estiver errado, toda análise ou resposta nova falha até alguém corrigir aqui. " +
          "Use \"Testar modelo\" para confirmar que ele responde.",
        confirmLabel: "Salvar assim",
        tone: "danger",
      });
      if (!confirmed) return;
    }

    try {
      await updateSettings.mutateAsync({
        daily_analysis_limit_per_owner: Number(analysisLimit),
        assistant_daily_message_limit: Number(messageLimit),
        analysis_model: analysisModel.trim(),
        analysis_temperature: Number(analysisTemperature),
        assistant_model: assistantModel.trim(),
        assistant_temperature: Number(assistantTemperature),
      });
      setFeedback("Configuração salva. Já vale para a próxima análise e para a próxima pergunta.");
    } catch (err) {
      setActionError(
        err instanceof ApiError ? err.message : "Erro ao salvar a configuração.",
      );
    }
  };

  const renderModelCard = (
    kind: ModelKind,
    {
      title,
      description,
      model,
      temperature,
      setTemperature,
      priced,
    }: {
      title: string;
      description: string;
      model: string;
      temperature: string;
      setTemperature: (v: string) => void;
      priced: boolean;
    },
  ) => {
    const reasoning = isReasoningModel(model, prefixes);
    const result = testResults[kind];

    return (
      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 4 }}>{title}</h3>
        <p className="page-subtitle" style={{ marginBottom: 16 }}>
          {description}
        </p>

        <div className="form-row">
          <div className="form-field">
            <label htmlFor={`${kind}-model`}>Modelo</label>
            <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
              <input
                id={`${kind}-model`}
                type="text"
                value={model}
                onChange={(e) => handleModelChange(kind, e.target.value)}
                placeholder="ex.: gpt-6-luna"
                style={{ flex: 1 }}
              />
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => handleTestModel(kind)}
                disabled={testingKind !== null || !model.trim()}
                aria-label={`Testar modelo ${kind === "analysis" ? "da análise" : "do assistente"}`}
                style={{ height: 40, whiteSpace: "nowrap" }}
              >
                {testingKind === kind ? "Testando..." : "Testar modelo"}
              </button>
            </div>
          </div>
          <div className="form-field">
            <label htmlFor={`${kind}-temperature`}>Temperatura</label>
            <input
              id={`${kind}-temperature`}
              type="number"
              min="0"
              max="2"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(e.target.value)}
              disabled={reasoning}
            />
            {reasoning && (
              <span className="page-subtitle" style={{ fontSize: 12 }}>
                Modelos de raciocínio ignoram temperatura — o valor fica salvo, mas inerte.
              </span>
            )}
          </div>
        </div>

        {result && (
          <div
            style={{
              display: "flex",
              gap: 8,
              alignItems: "flex-start",
              marginTop: 4,
              color: result.ok ? "var(--content-positive)" : "var(--content-negative)",
            }}
          >
            <Icon name={result.ok ? "check_circle" : "error"} size={20} />
            <span style={{ fontSize: 13 }}>{result.message}</span>
          </div>
        )}

        {!priced && (
          <div className="info-banner" style={{ marginTop: 16 }}>
            <Icon name="info" size={20} />
            <span>
              Este modelo não tem preço cadastrado: as chamadas dele aparecem sem custo no
              painel financeiro até alguém registrar a vigência em{" "}
              <Link to="/custos-ia">Custos de IA</Link>.
            </span>
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      <div className="page-header">
        <div className="page-title-group">
          <h1>Configurações</h1>
          <span className="page-subtitle">
            O que é salvo aqui vale imediatamente, sem reinício e sem nova versão da aplicação.
            As variáveis de ambiente servem apenas de ponto de partida e não sobrepõem estes
            valores.
          </span>
        </div>
      </div>

      {settings.isLoading && (
        <p className="page-subtitle" style={{ marginTop: 20 }}>
          Carregando...
        </p>
      )}
      {settings.isError && (
        <p className="error-text" style={{ marginTop: 20 }}>
          Não foi possível carregar as configurações.
        </p>
      )}

      {settings.data && (
        <div style={{ marginTop: 20 }}>
          {actionError && <ErrorBanner>{actionError}</ErrorBanner>}
          {feedback && (
            <div className="info-banner" style={{ marginBottom: 16 }}>
              <Icon name="check_circle" size={20} />
              <span>{feedback}</span>
            </div>
          )}

          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ marginBottom: 4 }}>Limites de uso diário</h3>
            <p className="page-subtitle" style={{ marginBottom: 16 }}>
              Contagem por pessoa, reiniciada à meia-noite (UTC). Um administrador é isento do
              limite de análises apenas quando envia para si mesmo.
            </p>

            <div className="form-row">
              <div className="form-field">
                <label htmlFor="analysis-limit">Análises por dia, por colaborador</label>
                <input
                  id="analysis-limit"
                  type="number"
                  min="1"
                  max="100"
                  step="1"
                  value={analysisLimit}
                  onChange={(e) => setAnalysisLimit(e.target.value)}
                />
              </div>
              <div className="form-field">
                <label htmlFor="message-limit">Perguntas por dia ao assistente</label>
                <input
                  id="message-limit"
                  type="number"
                  min="1"
                  max="1000"
                  step="1"
                  value={messageLimit}
                  onChange={(e) => setMessageLimit(e.target.value)}
                />
              </div>
            </div>
          </div>

          {renderModelCard("analysis", {
            title: "Modelo da análise",
            description:
              "Usado nas sete etapas do pipeline que gera o relatório. É a maior fonte de custo " +
              "da plataforma — trocar por um modelo mais caro aparece na fatura do mês.",
            model: analysisModel,
            temperature: analysisTemperature,
            setTemperature: setAnalysisTemperature,
            priced: settings.data.analysis_model_priced,
          })}

          {renderModelCard("assistant", {
            title: "Modelo do assistente",
            description:
              "Usado só no chat do assistente de IA. Costuma ser um modelo mais barato que o da " +
              "análise, porque cada resposta é uma chamada curta.",
            model: assistantModel,
            temperature: assistantTemperature,
            setTemperature: setAssistantTemperature,
            priced: settings.data.assistant_model_priced,
          })}

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 16,
            }}
          >
            <span className="page-subtitle" style={{ fontSize: 12 }}>
              {settings.data.updated_at
                ? `Alterado por ${settings.data.updated_by_name ?? "usuário removido"} em ${formatDateTime(settings.data.updated_at)}.`
                : "Nunca alterado pela tela — os valores vêm do ambiente."}
            </span>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleSave}
              disabled={updateSettings.isPending}
              style={{ height: 40, whiteSpace: "nowrap" }}
            >
              {updateSettings.isPending ? "Salvando..." : "Salvar alterações"}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
