import { ClipboardList, PenLine, Target, Sparkles, Check, LucideIcon } from "lucide-react"
import { SSEEvent } from "../api"

const STAGE_META: Record<string, { label: string; Icon: LucideIcon }> = {
  plan:     { label: "Planner",  Icon: ClipboardList },
  write:    { label: "Writer",   Icon: PenLine },
  critique: { label: "Critic",   Icon: Target },
  edit:     { label: "Editor",   Icon: Sparkles },
}

interface Props { stages: SSEEvent[]; active: boolean }

export default function StreamingIndicator({ stages, active }: Props) {
  if (!active && stages.length === 0) return null
  return (
    <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginBottom: "0.4rem" }}>
      {stages.map((s, i) => {
        const meta = STAGE_META[s.name || ""]
        const Icon = meta?.Icon
        return (
          <span key={i} style={{
            fontSize: "0.75rem", padding: "0.15rem 0.5rem", borderRadius: 4,
            background: "rgba(79,70,229,0.25)", color: "#a5b4fc",
            display: "flex", alignItems: "center", gap: "0.3rem",
          }}>
            {Icon && <Icon size={12} />}
            {meta?.label ?? s.name}
            {s.score !== undefined && ` ${s.score.toFixed(2)}`}
            <Check size={11} style={{ opacity: 0.7 }} />
          </span>
        )
      })}
      {active && (
        <span style={{ fontSize: "0.75rem", padding: "0.15rem 0.5rem", borderRadius: 4,
                       background: "rgba(217,119,6,0.25)", color: "#fbbf24" }}>
          working…
        </span>
      )}
    </div>
  )
}
