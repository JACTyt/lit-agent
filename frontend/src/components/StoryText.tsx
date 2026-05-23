import { forwardRef } from "react"

interface Props {
  text: string
  editMode?: boolean
  onChange?: (text: string) => void
}

const StoryText = forwardRef<HTMLTextAreaElement, Props>(
  ({ text, editMode, onChange }, ref) => {
    if (editMode) {
      return (
        <textarea
          ref={ref}
          value={text}
          onChange={e => onChange?.(e.target.value)}
          spellCheck={false}
          style={{
            width: "100%", height: "100%", minHeight: 400,
            padding: "1.5rem", boxSizing: "border-box",
            background: "transparent", color: "#d1d5db",
            border: "none", outline: "none", resize: "none",
            lineHeight: 1.8, fontSize: "0.95rem", fontFamily: "inherit",
          }}
        />
      )
    }

    return (
      <div style={{ padding: "1.5rem", lineHeight: 1.8, fontSize: "0.95rem",
                    maxWidth: 720, color: "#d1d5db" }}>
        {text.split("\n").map((line, i) => (
          <p key={i} style={{ marginBottom: line ? "0.75rem" : "0" }}>{line}</p>
        ))}
      </div>
    )
  }
)

StoryText.displayName = "StoryText"
export default StoryText
