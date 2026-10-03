import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deactivateUser } from "../api/users";

export function useDeactivateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deactivateUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });
}
