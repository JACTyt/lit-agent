import { useChat } from "../hooks/useChat"
import MessageList from "./MessageList"
import ChatInput from "./ChatInput"

export default function ChatView() {
  const { messages, loading, send, clearHistory } = useChat()
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "0.6rem 1rem", borderBottom: "1px solid #2a2a35", flexShrink: 0 }}>
        <span style={{ fontSize: "0.9rem", opacity: 0.6 }}>💬 Chat</span>
        {messages.length > 0 && (
          <button
            onClick={clearHistory}
            style={{ background: "none", border: "1px solid #2a2a35", color: "#6b7280",
                     cursor: "pointer", fontSize: "0.72rem", padding: "0.15rem 0.5rem",
                     borderRadius: 4, lineHeight: 1.4 }}
          >
            Clear
          </button>
        )}
      </div>
      <MessageList messages={messages} />
      <ChatInput onSend={send} disabled={loading} />
    </div>
  )
}
