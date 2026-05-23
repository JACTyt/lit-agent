import { SSEEvent } from "../api"

const STAGE_LABELS: Record<string, string> = {
  plan: "📋 Planner",
  write: "✍️ Writer",
  critique: "🎯 Critic",
  edit: "✨ Editor",
}

interface Props { stages: SSEEvent[]; active: boolean }

export default function StreamingIndicator({ stages, active }: Props) {
  if (!active && stages.length === 0) return null
  return (
    <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginBottom: "0.4rem" }}>
      {stages.map((s, i) => (
        <span key={i} style={{
          fontSize: "0.75rem", padding: "0.15rem 0.5rem", borderRadius: 4,
          background: "rgba(79,70,229,0.25)", color: "#a5b4fc",
        }}>
          {STAGE_LABELS[s.name || ""] || s.name} {s.score !== undefined ? `${s.score.toFixed(2)}` : ""} ✓
        </span>
      ))}
      {active && (
        <span style={{ fontSize: "0.75rem", padding: "0.15rem 0.5rem", borderRadius: 4,
                       background: "rgba(217,119,6,0.25)", color: "#fbbf24" }}>
          working…
        </span>
      )}
    </div>
  )
}
