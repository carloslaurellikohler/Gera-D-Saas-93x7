import { useQuery } from "@tanstack/react-query";
import { listMethodologies } from "../api/methodology";

export function useMethodologies() {
  return useQuery({
    queryKey: ["methodology"],
    queryFn: listMethodologies,
  });
}
