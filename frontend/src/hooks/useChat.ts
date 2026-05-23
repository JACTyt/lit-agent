import { useState, useCallback } from "react"
import { api, SSEEvent } from "../api"
import { useStream } from "./useStream"

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  loading?: boolean
  stages?: SSEEvent[]
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const { connect } = useStream()

  const send = useCallback(async (text: string) => {
    if (!text.trim()) return
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: text }
    const pendingId = crypto.randomUUID()
    const pendingMsg: ChatMessage = { id: pendingId, role: "assistant", content: "", loading: true, stages: [] }
    setMessages(prev => [...prev, userMsg, pendingMsg])
    setLoading(true)

    try {
      const { run_id } = await api.chat(text)
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
  }, [connect])

  return { messages, loading, send }
}
