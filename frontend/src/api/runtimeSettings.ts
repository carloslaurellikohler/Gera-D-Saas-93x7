import type {
  ModelTestPayload,
  ModelTestResult,
  RuntimeSettings,
  RuntimeSettingsPayload,
} from "../types/runtimeSettings";
import { apiGet, apiPost, apiPut } from "./client";

export function getRuntimeSettings() {
  return apiGet<RuntimeSettings>("/settings");
}

export function updateRuntimeSettings(payload: RuntimeSettingsPayload) {
  return apiPut<RuntimeSettings>("/settings", payload);
}

/** Valida um nome de modelo digitado antes de salvar. Nada é persistido. */
export function testAiModel(payload: ModelTestPayload) {
  return apiPost<ModelTestResult>("/settings/test-model", payload);
}
