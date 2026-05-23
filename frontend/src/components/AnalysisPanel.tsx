import { Analysis } from "../api"

export default function AnalysisPanel({ analysis }: { analysis?: Analysis }) {
  if (!analysis || !analysis.motivation) {
    return (
      <div style={{ padding: "1rem", opacity: 0.4, fontSize: "0.82rem" }}>
        No analysis yet — ask LitBot to analyse this story.
      </div>
    )
  }
  const sections: [string, string | string[] | { moment: string; explanation: string }[] | undefined][] = [
    ["Motivation", analysis.motivation],
    ["Thesis", analysis.thesis],
    ["Emotional arc", analysis.emotional_arc],
    ["Description", analysis.brief_description],
    ["Themes", analysis.thoughts],
    ["Key moments", analysis.key_moments],
  ]
  return (
    <div style={{ padding: "1rem" }}>
      <div style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.08em",
                    opacity: 0.4, marginBottom: "0.75rem" }}>Analysis</div>
      {sections.map(([label, val]) => val ? (
        <div key={label} style={{ marginBottom: "0.75rem" }}>
          <div style={{ fontSize: "0.75rem", opacity: 0.5, marginBottom: "0.2rem" }}>{label}</div>
          {Array.isArray(val) && typeof val[0] === "string"
            ? <ul style={{ paddingLeft: "1rem", fontSize: "0.85rem" }}>{(val as string[]).map((t, i) => <li key={i}>{t}</li>)}</ul>
            : Array.isArray(val)
              ? (val as { moment: string; explanation: string }[]).map((m, i) => (
                  <div key={i} style={{ fontSize: "0.85rem", marginBottom: "0.3rem" }}>
                    <strong>{m.moment}</strong> — {m.explanation}
                  </div>
                ))
              : <div style={{ fontSize: "0.85rem" }}>{String(val)}</div>
          }
        </div>
      ) : null)}
    </div>
  )
}
