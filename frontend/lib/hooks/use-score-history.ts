import { useQuery } from "@tanstack/react-query";
import { fetchScoreHistory } from "@/lib/api";

export function useScoreHistory() {
  return useQuery({
    queryKey: ["score-history"],
    queryFn: fetchScoreHistory,
  });
}
