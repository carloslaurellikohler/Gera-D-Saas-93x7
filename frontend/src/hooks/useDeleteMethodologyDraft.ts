import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteMethodologyDraft } from "../api/methodology";

export function useDeleteMethodologyDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteMethodologyDraft(id),
    // `removeQueries` é o que impede o rascunho excluído de continuar na tela: sem ele o
    // refetch do detalhe devolve 404 e o react-query mantém o `data` anterior, deixando um
    // rascunho morto renderizável até um F5.
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: ["methodology", id] });
      return queryClient.invalidateQueries({ queryKey: ["methodology"], exact: true });
    },
  });
}
