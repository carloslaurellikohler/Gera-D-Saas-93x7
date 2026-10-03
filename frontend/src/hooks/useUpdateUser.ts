import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateUser } from "../api/users";
import type { UpdateUserPayload } from "../types/user";

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateUserPayload }) =>
      updateUser(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });
}
