import { useMutation, useQueryClient } from "@tanstack/react-query";
import { resetUserPassword } from "../api/users";
import type { ResetPasswordPayload } from "../types/user";

export function useResetUserPassword() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ResetPasswordPayload }) =>
      resetUserPassword(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });
}
