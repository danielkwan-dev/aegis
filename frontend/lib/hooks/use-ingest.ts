import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ingestExport, ingestManual } from "@/lib/api";

export function useIngestManual() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ingestManual,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["footprint"] });
    },
  });
}

export function useIngestExport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ingestExport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["footprint"] });
    },
  });
}
