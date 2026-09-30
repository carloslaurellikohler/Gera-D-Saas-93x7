import { useQuery } from "@tanstack/react-query";
import { getAnalysis, getAnalysisResult, getTranscription } from "../api/analyses";

export function useAnalysis(id: string) {
  return useQuery({
    queryKey: ["analysis", id],
    queryFn: () => getAnalysis(id),
  });
}

export function useTranscription(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["transcription", id],
    queryFn: () => getTranscription(id),
    enabled,
  });
}

export function useAnalysisResult(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["analysis-result", id],
    queryFn: () => getAnalysisResult(id),
    enabled,
  });
}
