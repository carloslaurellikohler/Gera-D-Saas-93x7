import { useMutation, useQueryClient } from "@tanstack/react-query";
import { activateUser } from "../api/users";

export function useActivateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: activateUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });
}
