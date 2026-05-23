import { useState } from "react"
import { Pencil, Check, X, Plus, Trash2 } from "lucide-react"
import { Analysis } from "../api"
import { useUpdateAnalysis } from "../hooks/useLibrary"

interface Props {
  bookName: string
  analysis?: Analysis
}

interface DraftAnalysis {
  motivation: string
  thesis: string
  emotional_arc: string
  brief_description: string
  thoughtsText: string                                // one thought per line
  key_moments: { moment: string; explanation: string }[]
}

const inputStyle: React.CSSProperties = {
  width: "100%", boxSizing: "border-box",
  background: "#1a1a24", border: "1px solid #2a2a35", color: "#d1d5db",
  borderRadius: 4, padding: "0.2rem 0.4rem", fontSize: "0.82rem",
}

const taStyle: React.CSSProperties = {
  ...inputStyle, resize: "vertical" as const, minHeight: 56, lineHeight: 1.5,
}

const panelBtn: React.CSSProperties = {
  background: "none", border: "none", cursor: "pointer",
  padding: "0.1rem 0.25rem", borderRadius: 3,
  display: "flex", alignItems: "center",
}

const labelStyle: React.CSSProperties = {
  fontSize: "0.68rem", opacity: 0.4, marginBottom: "0.12rem",
}

function toDraft(a?: Analysis): DraftAnalysis {
  return {
    motivation:        a?.motivation        ?? "",
    thesis:            a?.thesis            ?? "",
    emotional_arc:     a?.emotional_arc     ?? "",
    brief_description: a?.brief_description ?? "",
    thoughtsText:      (a?.thoughts ?? []).join("\n"),
    key_moments:       a?.key_moments ? a.key_moments.map(m => ({ ...m })) : [],
  }
}

function fromDraft(d: DraftAnalysis): Partial<Analysis> {
  return {
    motivation:        d.motivation        || undefined,
    thesis:            d.thesis            || undefined,
    emotional_arc:     d.emotional_arc     || undefined,
    brief_description: d.brief_description || undefined,
    thoughts:          d.thoughtsText.trim()
                         ? d.thoughtsText.split("\n").map(s => s.trim()).filter(Boolean)
                         : undefined,
    key_moments:       d.key_moments.filter(m => m.moment || m.explanation).length
                         ? d.key_moments.filter(m => m.moment || m.explanation)
                         : undefined,
  }
}

export default function AnalysisPanel({ bookName, analysis }: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<DraftAnalysis>(toDraft())
  const save = useUpdateAnalysis(bookName)

  function enterEdit() {
    setDraft(toDraft(analysis))
    setEditing(true)
  }

  async function handleSave() {
    await save.mutateAsync(fromDraft(draft))
    setEditing(false)
  }

  function setField<K extends keyof DraftAnalysis>(k: K, v: DraftAnalysis[K]) {
    setDraft(d => ({ ...d, [k]: v }))
  }

  function setMoment(i: number, field: "moment" | "explanation", v: string) {
    setDraft(d => {
      const km = d.key_moments.map((m, j) => j === i ? { ...m, [field]: v } : m)
      return { ...d, key_moments: km }
    })
  }

  function addMoment() {
    setDraft(d => ({ ...d, key_moments: [...d.key_moments, { moment: "", explanation: "" }] }))
  }

  function removeMoment(i: number) {
    setDraft(d => ({ ...d, key_moments: d.key_moments.filter((_, j) => j !== i) }))
  }

  const hasData = analysis && analysis.motivation

  return (
    <div style={{ padding: "1rem" }}>
      <div style={{ display: "flex", alignItems: "center", marginBottom: "0.75rem" }}>
        <div style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.08em", opacity: 0.4, flex: 1 }}>
          Analysis
        </div>
        {!editing ? (
          <button style={{ ...panelBtn, color: "#6b7280" }} onClick={enterEdit} title="Edit analysis">
            <Pencil size={12} />
          </button>
        ) : (
          <div style={{ display: "flex", gap: "0.3rem" }}>
            <button style={{ ...panelBtn, color: "#4ade80" }} onClick={handleSave}
              title="Save" disabled={save.isPending}>
              <Check size={13} />
            </button>
            <button style={{ ...panelBtn, color: "#9ca3af" }} onClick={() => setEditing(false)} title="Cancel">
              <X size={13} />
            </button>
          </div>
        )}
      </div>

      {!editing && !hasData && (
        <div style={{ opacity: 0.4, fontSize: "0.82rem" }}>
          No analysis yet — ask LitBot to analyse this story.
        </div>
      )}

      {editing ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>

          {(["motivation", "thesis", "emotional_arc", "brief_description"] as const).map(f => (
            <div key={f}>
              <div style={labelStyle}>{f.replace(/_/g, " ")}</div>
              <textarea
                value={draft[f]}
                onChange={e => setField(f, e.target.value)}
                style={taStyle}
              />
            </div>
          ))}

          <div>
            <div style={labelStyle}>Themes (one per line)</div>
            <textarea
              value={draft.thoughtsText}
              onChange={e => setField("thoughtsText", e.target.value)}
              style={{ ...taStyle, minHeight: 72 }}
              placeholder="One theme per line…"
            />
          </div>

          <div>
            <div style={{ ...labelStyle, marginBottom: "0.3rem" }}>Key moments</div>
            {draft.key_moments.map((m, i) => (
              <div key={i} style={{ marginBottom: "0.4rem", padding: "0.4rem",
                                    background: "rgba(255,255,255,0.02)", borderRadius: 5,
                                    border: "1px solid #1e1e2a" }}>
                <div style={{ display: "flex", gap: "0.3rem", alignItems: "flex-start" }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ ...labelStyle, marginBottom: "0.1rem" }}>Moment</div>
                    <input value={m.moment} onChange={e => setMoment(i, "moment", e.target.value)}
                      style={inputStyle} placeholder="Scene or event…" />
                    <div style={{ ...labelStyle, marginTop: "0.3rem", marginBottom: "0.1rem" }}>Explanation</div>
                    <textarea value={m.explanation} onChange={e => setMoment(i, "explanation", e.target.value)}
                      style={{ ...taStyle, minHeight: 44 }} placeholder="Why it matters…" />
                  </div>
                  <button onClick={() => removeMoment(i)}
                    style={{ ...panelBtn, color: "#6b7280", marginTop: 2 }} title="Remove">
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            ))}
            <button onClick={addMoment}
              style={{ ...panelBtn, border: "1px dashed #2a2a35", color: "#6b7280",
                       padding: "0.2rem 0.5rem", fontSize: "0.74rem", gap: "0.25rem", borderRadius: 4 }}>
              <Plus size={12} /> Add moment
            </button>
          </div>

        </div>
      ) : hasData ? (
        <div>
          {([
            ["Motivation",    analysis!.motivation],
            ["Thesis",        analysis!.thesis],
            ["Emotional arc", analysis!.emotional_arc],
            ["Description",   analysis!.brief_description],
          ] as [string, string | undefined][]).map(([label, val]) => val ? (
            <div key={label} style={{ marginBottom: "0.75rem" }}>
              <div style={{ fontSize: "0.75rem", opacity: 0.5, marginBottom: "0.2rem" }}>{label}</div>
              <div style={{ fontSize: "0.85rem" }}>{val}</div>
            </div>
          ) : null)}

          {analysis!.thoughts?.length ? (
            <div style={{ marginBottom: "0.75rem" }}>
              <div style={{ fontSize: "0.75rem", opacity: 0.5, marginBottom: "0.2rem" }}>Themes</div>
              <ul style={{ paddingLeft: "1rem", fontSize: "0.85rem", margin: 0 }}>
                {analysis!.thoughts.map((t, i) => <li key={i}>{t}</li>)}
              </ul>
            </div>
          ) : null}

          {analysis!.key_moments?.length ? (
            <div>
              <div style={{ fontSize: "0.75rem", opacity: 0.5, marginBottom: "0.2rem" }}>Key moments</div>
              {analysis!.key_moments.map((m, i) => (
                <div key={i} style={{ fontSize: "0.85rem", marginBottom: "0.3rem" }}>
                  <strong>{m.moment}</strong> — {m.explanation}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
