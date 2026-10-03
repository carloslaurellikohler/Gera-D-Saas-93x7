import { useMutation, useQueryClient } from "@tanstack/react-query";
import { publishMethodology } from "../api/methodology";

export function usePublishMethodology() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => publishMethodology(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["methodology"] });
    },
  });
}
