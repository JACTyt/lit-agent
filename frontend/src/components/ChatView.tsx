import { useChat } from "../hooks/useChat"
import MessageList from "./MessageList"
import ChatInput from "./ChatInput"

export default function ChatView() {
  const { messages, loading, send } = useChat()
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <div style={{ padding: "0.75rem 1rem", borderBottom: "1px solid #2a2a35",
                    fontSize: "0.9rem", opacity: 0.6 }}>
        💬 Chat
      </div>
      <MessageList messages={messages} />
      <ChatInput onSend={send} disabled={loading} />
    </div>
  )
}
