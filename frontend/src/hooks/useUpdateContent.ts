import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateContent } from "../api/content";
import type { UpdateContentPayload } from "../types/content";

export function useUpdateContent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateContentPayload }) =>
      updateContent(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["content"] });
    },
  });
}
