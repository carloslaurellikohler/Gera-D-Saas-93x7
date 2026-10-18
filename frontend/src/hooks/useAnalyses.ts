import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { listAnalyses } from "../api/analyses";
import type { AnalysisFilters } from "../types/analysis";

export function useAnalyses(filters: AnalysisFilters = {}) {
  return useQuery({
    queryKey: ["analyses", filters],
    queryFn: () => listAnalyses(filters),
    // Mantém a lista/filtros visíveis durante o refetch ao trocar um filtro — sem isso,
    // cada tecla/seleção muda a queryKey e isLoading volta a true, derrubando a tabela
    // e os próprios controles de filtro por um instante.
    placeholderData: keepPreviousData,
  });
}
