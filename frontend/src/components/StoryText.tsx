export default function StoryText({ text }: { text: string }) {
  return (
    <div style={{ padding: "1.5rem", lineHeight: 1.8, fontSize: "0.95rem",
                  maxWidth: 720, color: "#d1d5db" }}>
      {text.split("\n").map((line, i) => (
        <p key={i} style={{ marginBottom: line ? "0.75rem" : "0" }}>{line}</p>
      ))}
    </div>
  )
}
