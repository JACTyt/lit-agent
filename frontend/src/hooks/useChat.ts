import { useState, useCallback, useEffect } from "react"
import { api, SSEEvent } from "../api"
import { useStream } from "./useStream"

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  loading?: boolean
  stages?: SSEEvent[]
}

const STORAGE_KEY = "chat.history"
const MAX_STORED = 100

function loadMessages(): ChatMessage[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed: ChatMessage[] = JSON.parse(raw)
    return parsed.map(m => ({ ...m, loading: false }))
  } catch {
    return []
  }
}

function saveMessages(messages: ChatMessage[]) {
  try {
    const finished = messages.filter(m => !m.loading).slice(-MAX_STORED)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(finished))
  } catch {}
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>(loadMessages)
  const [loading, setLoading] = useState(false)
  const { connect } = useStream()

  useEffect(() => {
    saveMessages(messages)
  }, [messages])

  const clearHistory = useCallback(() => {
    setMessages([])
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  const send = useCallback(async (text: string) => {
    if (!text.trim()) return
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: text }
    const pendingId = crypto.randomUUID()
    const pendingMsg: ChatMessage = { id: pendingId, role: "assistant", content: "", loading: true, stages: [] }

    // Capture history before we add the new messages to state
    const history = messages
      .filter(m => !m.loading)
      .map(m => ({ role: m.role as "user" | "assistant", content: m.content }))

    setMessages(prev => [...prev, userMsg, pendingMsg])
    setLoading(true)

    try {
      const { run_id } = await api.chat(text, history)
      connect(
        run_id,
        (token) => setMessages(prev => prev.map(m =>
          m.id === pendingId ? { ...m, content: m.content + token } : m
        )),
        (stage) => setMessages(prev => prev.map(m =>
          m.id === pendingId ? { ...m, stages: [...(m.stages || []), stage] } : m
        )),
        (reply) => {
          setMessages(prev => prev.map(m =>
            m.id === pendingId
              ? { ...m, content: reply || m.content, loading: false }
              : m
          ))
          setLoading(false)
        },
      )
    } catch (err) {
      setMessages(prev => prev.map(m =>
        m.id === pendingId
          ? { ...m, content: `Error: ${err instanceof Error ? err.message : String(err)}`, loading: false }
          : m
      ))
      setLoading(false)
    }
  }, [connect, messages])

  return { messages, loading, send, clearHistory }
}
