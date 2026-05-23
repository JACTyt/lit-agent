import { useState, KeyboardEvent } from "react"

interface Props { onSend: (text: string) => void; disabled: boolean }

export default function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState("")

  const submit = () => {
    if (!value.trim() || disabled) return
    onSend(value.trim())
    setValue("")
  }

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit() }
  }

  return (
    <div style={{ padding: "0.75rem 1rem", borderTop: "1px solid #2a2a35",
                  display: "flex", gap: "0.5rem", background: "#0f0f13" }}>
      <textarea
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={onKey}
        disabled={disabled}
        rows={2}
        placeholder="Ask LitBot anything… (Enter to send)"
        style={{ flex: 1, background: "#1e1e2e", border: "1px solid #2a2a35", borderRadius: 8,
                 padding: "0.5rem 0.75rem", color: "#e5e7eb", fontSize: "0.9rem",
                 resize: "none", outline: "none", fontFamily: "inherit" }}
      />
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        style={{ padding: "0 1rem", background: "#4f46e5", color: "#fff", border: "none",
                 borderRadius: 8, cursor: "pointer", fontWeight: 600, fontSize: "0.9rem",
                 opacity: disabled ? 0.5 : 1 }}
      >
        Send
      </button>
    </div>
  )
}
