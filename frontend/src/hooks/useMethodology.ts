import { useQuery } from "@tanstack/react-query";
import { getMethodology } from "../api/methodology";

export function useMethodology(id: string | null) {
  return useQuery({
    queryKey: ["methodology", id],
    queryFn: () => getMethodology(id as string),
    enabled: id !== null,
  });
}
