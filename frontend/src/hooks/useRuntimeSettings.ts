import { useQuery } from "@tanstack/react-query";
import { getRuntimeSettings } from "../api/runtimeSettings";

export function useRuntimeSettings() {
  return useQuery({ queryKey: ["settings", "config"], queryFn: getRuntimeSettings });
}
