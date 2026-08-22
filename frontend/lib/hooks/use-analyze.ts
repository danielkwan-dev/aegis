import { useMutation, useQueryClient } from "@tanstack/react-query";
import { analyzeThreat } from "@/lib/api";

export function useAnalyze() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: analyzeThreat,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["score-history"] });
    },
  });
}
