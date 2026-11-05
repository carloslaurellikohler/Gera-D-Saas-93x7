import { useMutation, useQueryClient } from "@tanstack/react-query";
import { publishMethodology } from "../api/methodology";

export function usePublishMethodology() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => publishMethodology(id),
    // Aqui a invalidação é por prefixo de propósito: publicar encerra a versão que estava
    // ativa, então o detalhe dela em cache também envelheceu.
    onSuccess: (published, id) => {
      queryClient.setQueryData(["methodology", id], published);
      return queryClient.invalidateQueries({ queryKey: ["methodology"] });
    },
  });
}
