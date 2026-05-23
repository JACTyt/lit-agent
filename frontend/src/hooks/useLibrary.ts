import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api, Classification, Analysis, CharacterData } from "../api"

export function useLibrary() {
  return useQuery({ queryKey: ["library"], queryFn: api.library, staleTime: 30_000 })
}

export function useBook(name: string) {
  return useQuery({ queryKey: ["book", name], queryFn: () => api.book(name), enabled: !!name })
}

export function useAnalysis(name: string) {
  return useQuery({ queryKey: ["analysis", name], queryFn: () => api.analysis(name), enabled: !!name })
}

export function useUpdateBook(name: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (text: string) => api.updateBookText(name, text),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["book", name] })
      qc.invalidateQueries({ queryKey: ["library"] })
    },
  })
}

export function useUpdateMetadata(name: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (classification: Partial<Classification>) => api.updateMetadata(name, classification),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["book", name] })
      qc.invalidateQueries({ queryKey: ["library"] })
    },
  })
}

export function useUpdateAnalysis(name: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (analysis: Partial<Analysis>) => api.updateAnalysis(name, analysis),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["analysis", name] })
    },
  })
}

export function useUpdateCharacters(name: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CharacterData) => api.updateCharacters(name, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["characters", name] })
    },
  })
}
