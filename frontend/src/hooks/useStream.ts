import { useCallback, useRef } from "react"
import { SSEEvent } from "../api"

export function useStream() {
  const esRef = useRef<EventSource | null>(null)

  const connect = useCallback((
    runId: string,
    onToken: (text: string) => void,
    onStage: (event: SSEEvent) => void,
    onDone: (reply: string) => void,
  ) => {
    if (esRef.current) esRef.current.close()
    const es = new EventSource(`/api/stream/${runId}`)
    esRef.current = es

    es.onmessage = (e) => {
      try {
        const event: SSEEvent & { reply?: string } = JSON.parse(e.data)
        if (event.type === "token" && event.text) onToken(event.text)
        else if (event.type === "stage") onStage(event)
        else if (event.type === "done") {
          onDone(event.reply || "")
          es.close()
        }
      } catch {/* ignore parse errors */}
    }

    es.onerror = () => {
      onDone("[stream error]")
      es.close()
    }
  }, [])

  const close = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
  }, [])

  return { connect, close }
}
