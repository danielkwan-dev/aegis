import { useQuery } from "@tanstack/react-query";
import { fetchFootprint } from "@/lib/api";

export function useFootprint() {
  return useQuery({
    queryKey: ["footprint"],
    queryFn: fetchFootprint,
  });
}
