// Espelho manual dos schemas pydantic de backend/app/schemas/runtime_settings.py.

export interface RuntimeSettings {
  daily_analysis_limit_per_owner: number;
  assistant_daily_message_limit: number;
  analysis_model: string;
  analysis_temperature: number;
  assistant_model: string;
  assistant_temperature: number;
  // Lista vinda do backend (app/services/assistant_llm.py) para não manter uma cópia aqui:
  // modelo de raciocínio ignora temperatura, e a tela desabilita o campo.
  reasoning_model_prefixes: string[];
  // Falso quando o modelo não tem preço cadastrado — as chamadas vão cair em NO_PRICE no FinAI.
  analysis_model_priced: boolean;
  assistant_model_priced: boolean;
  // Auditoria do último editor apenas; null enquanto nunca foi editado pela tela.
  updated_at: string | null;
  updated_by_name: string | null;
}

export interface RuntimeSettingsPayload {
  daily_analysis_limit_per_owner: number;
  assistant_daily_message_limit: number;
  analysis_model: string;
  analysis_temperature: number;
  assistant_model: string;
  assistant_temperature: number;
}

export interface ModelTestPayload {
  model_name: string;
  temperature?: number | null;
}

export interface ModelTestResult {
  ok: boolean;
  message: string;
}
