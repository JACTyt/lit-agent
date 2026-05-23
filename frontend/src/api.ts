const BASE = "/api"

export interface Classification {
  title: string
  genre: string
  theme: string
  audience: string
  reading_level: string
  moral: string
}

export interface EditEntry {
  timestamp: string
  instruction: string
  section_hint: string | null
}

export interface BookSummary {
  book_name: string
  source_path: string
  classification: Partial<Classification>
  version: number
}

export interface BookDetail extends BookSummary {
  text: string
  analysis?: Analysis
  edit_history?: EditEntry[]
  characters_path?: string | null
  pipeline?: PipelineMeta
}

export interface Analysis {
  motivation?: string
  thesis?: string
  thoughts?: string[]
  key_moments?: { moment: string; explanation: string }[]
  brief_description?: string
  emotional_arc?: string
}

export interface PipelineMeta {
  critic_score?: number
  critic_passes?: number
  stages_completed?: string[]
}

export interface CharacterData {
  version: number
  story: string
  extracted_at: string
  world: { setting: string; time_period: string; tone: string }
  characters: Character[]
}

export interface Character {
  name: string
  role: string
  traits: string[]
  arc: string
  first_appears: string
}

export interface HealthInfo {
  provider: string
  model: string
  status: string
}

export interface ChatResponse {
  run_id: string
  status?: string
  reply?: string
}

export interface SSEEvent {
  type: "token" | "stage" | "tool_call" | "done"
  text?: string
  name?: string
  score?: number
  tool?: string
  saved_path?: string
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API error ${res.status}: ${detail}`)
  }
  return res.json()
}

export const api = {
  health: () => apiFetch<HealthInfo>("/health"),
  library: () => apiFetch<BookSummary[]>("/library"),
  book: (name: string) => apiFetch<BookDetail>(`/library/${name}`),
  analysis: (name: string) => apiFetch<Analysis>(`/library/${name}/analysis`),
  characters: (name: string) => apiFetch<CharacterData>(`/library/${name}/characters`),
  chat: (message: string, history: Array<{ role: string; content: string }> = []) =>
    apiFetch<ChatResponse>("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    }),
  reimport: () => apiFetch<{ status: string; vectors: number }>("/reimport", { method: "POST" }),
}
