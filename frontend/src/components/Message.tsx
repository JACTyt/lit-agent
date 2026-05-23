import { ChatMessage } from "../hooks/useChat"
import StreamingIndicator from "./StreamingIndicator"

const s: Record<string, React.CSSProperties> = {
  row: { display: "flex", gap: "0.5rem", alignItems: "flex-start", marginBottom: "0.75rem" },
  rowReverse: { flexDirection: "row-reverse" },
  avatar: { width: 28, height: 28, borderRadius: "50%", display: "flex",
            alignItems: "center", justifyContent: "center", fontSize: "0.75rem",
            flexShrink: 0, fontWeight: 700 },
  bubble: { maxWidth: "80%", padding: "0.5rem 0.85rem", borderRadius: 10,
            fontSize: "0.9rem", lineHeight: 1.55, whiteSpace: "pre-wrap" },
}

export default function Message({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user"
  return (
    <div style={{ ...s.row, ...(isUser ? s.rowReverse : {}) }}>
      <div style={{ ...s.avatar, background: isUser ? "#4f46e5" : "#7c3aed" }}>
        {isUser ? "Y" : "B"}
      </div>
      <div style={{ display: "flex", flexDirection: "column", maxWidth: "80%" }}>
        {!isUser && <StreamingIndicator stages={msg.stages || []} active={!!msg.loading} />}
        <div style={{
          ...s.bubble,
          background: isUser ? "rgba(79,70,229,0.18)" : "rgba(124,58,237,0.18)",
        }}>
          {msg.loading && !msg.content
            ? <span style={{ opacity: 0.5 }}>Thinking…</span>
            : msg.content}
          {msg.loading && msg.content && <span style={{ opacity: 0.4 }}>▋</span>}
        </div>
      </div>
    </div>
  )
}
