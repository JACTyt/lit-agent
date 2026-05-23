import { useState } from "react"
import { Pencil, Check, X } from "lucide-react"
import { Classification, PipelineMeta } from "../api"
import { useUpdateMetadata } from "../hooks/useLibrary"

interface Props {
  bookName: string
  classification?: Partial<Classification>
  pipeline?: PipelineMeta
}

const FIELDS: { key: keyof Classification; label: string }[] = [
  { key: "title",         label: "Title" },
  { key: "genre",         label: "Genre" },
  { key: "theme",         label: "Theme" },
  { key: "audience",      label: "Audience" },
  { key: "reading_level", label: "Reading level" },
  { key: "moral",         label: "Moral" },
]

const inputStyle: React.CSSProperties = {
  width: "100%", boxSizing: "border-box",
  background: "#1a1a24", border: "1px solid #2a2a35", color: "#d1d5db",
  borderRadius: 4, padding: "0.2rem 0.4rem", fontSize: "0.82rem",
}

const panelBtn: React.CSSProperties = {
  background: "none", border: "none", cursor: "pointer",
  padding: "0.1rem 0.25rem", borderRadius: 3,
  display: "flex", alignItems: "center",
}

export default function MetadataPanel({ bookName, classification = {}, pipeline }: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<Partial<Classification>>({})
  const save = useUpdateMetadata(bookName)

  function enterEdit() {
    setDraft({ ...classification })
    setEditing(true)
  }

  async function handleSave() {
    await save.mutateAsync(draft)
    setEditing(false)
  }

  const rows = FIELDS.filter(({ key }) => classification[key])

  return (
    <div style={{ padding: "1rem", borderBottom: "1px solid #2a2a35" }}>
      <div style={{ display: "flex", alignItems: "center", marginBottom: "0.5rem" }}>
        <div style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.08em", opacity: 0.4, flex: 1 }}>
          Metadata
        </div>
        {!editing ? (
          <button style={{ ...panelBtn, color: "#6b7280" }} onClick={enterEdit} title="Edit metadata">
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

      {editing ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem" }}>
          {FIELDS.map(({ key, label }) => (
            <div key={key}>
              <div style={{ fontSize: "0.68rem", opacity: 0.4, marginBottom: "0.12rem" }}>{label}</div>
              <input
                value={draft[key] ?? ""}
                onChange={e => setDraft(d => ({ ...d, [key]: e.target.value }))}
                style={inputStyle}
              />
            </div>
          ))}
        </div>
      ) : (
        <table style={{ borderCollapse: "collapse", fontSize: "0.82rem", width: "100%" }}>
          <tbody>
            {rows.map(({ key, label }) => (
              <tr key={key}>
                <td style={{ padding: "0.2rem 0.5rem 0.2rem 0", opacity: 0.5, whiteSpace: "nowrap" }}>{label}</td>
                <td style={{ padding: "0.2rem 0" }}>{String(classification[key])}</td>
              </tr>
            ))}
            {pipeline?.critic_score !== undefined && (
              <tr>
                <td style={{ padding: "0.2rem 0.5rem 0.2rem 0", opacity: 0.5 }}>Critic score</td>
                <td>{pipeline.critic_score.toFixed(2)}</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
