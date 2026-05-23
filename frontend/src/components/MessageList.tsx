import { useEffect, useRef } from "react"
import { ChatMessage } from "../hooks/useChat"
import Message from "./Message"

export default function MessageList({ messages }: { messages: ChatMessage[] }) {
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "1rem" }}>
      {messages.length === 0 && (
        <div style={{ opacity: 0.35, textAlign: "center", marginTop: "3rem", fontSize: "0.9rem" }}>
          Ask LitBot to create a story, classify a book, or analyse a character…
        </div>
      )}
      {messages.map(m => <Message key={m.id} msg={m} />)}
      <div ref={bottomRef} />
    </div>
  )
}
