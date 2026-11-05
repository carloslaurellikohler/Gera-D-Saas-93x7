import { useQuery } from "@tanstack/react-query";
import { getMethodologyPromptPreview } from "../api/methodology";

/**
 * O prompt compilado muda a cada salvamento do rascunho, então esta query é invalidada
 * explicitamente por useUpdateMethodologyDraft.
 */
export function useMethodologyPromptPreview(id: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ["methodology", id, "prompt-preview"],
    queryFn: () => getMethodologyPromptPreview(id as string),
    enabled: id !== null && enabled,
  });
}
