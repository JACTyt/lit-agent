import { useQuery } from "@tanstack/react-query"
import { api } from "../api"

export function useLibrary() {
  return useQuery({ queryKey: ["library"], queryFn: api.library, staleTime: 30_000 })
}

export function useBook(name: string) {
  return useQuery({ queryKey: ["book", name], queryFn: () => api.book(name), enabled: !!name })
}

export function useAnalysis(name: string) {
  return useQuery({ queryKey: ["analysis", name], queryFn: () => api.analysis(name), enabled: !!name })
}
