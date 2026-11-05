import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createMethodologyDraft } from "../api/methodology";

export function useCreateMethodologyDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fromId?: string) => createMethodologyDraft(fromId),
    // O POST já devolve o MethodologyDetail completo: semear o cache evita que o editor
    // abra vazio enquanto um GET redundante está em voo. Daí o `exact: true` — invalidar
    // por prefixo marcaria como stale justamente o detalhe recém-semeado.
    onSuccess: (created) => {
      queryClient.setQueryData(["methodology", created.id], created);
      return queryClient.invalidateQueries({ queryKey: ["methodology"], exact: true });
    },
  });
}
