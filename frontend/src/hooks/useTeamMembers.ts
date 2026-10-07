import { useQuery } from "@tanstack/react-query";
import { listMyTeam } from "../api/users";
import { useAuth } from "../context/AuthContext";

export function useTeamMembers() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["users", "me", "team"],
    queryFn: listMyTeam,
    enabled: user?.role === "GESTOR",
  });
}
