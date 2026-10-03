import { useQuery } from "@tanstack/react-query";
import { listUsers } from "../api/users";
import type { UserFilters } from "../types/user";

export function useUsers(filters: UserFilters = {}) {
  return useQuery({
    queryKey: ["users", filters],
    queryFn: () => listUsers(filters),
  });
}
