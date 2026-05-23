import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Globe, Pencil, Check, X, Plus, Trash2 } from "lucide-react"
import { api, Character, CharacterData } from "../api"
import { useUpdateCharacters } from "../hooks/useLibrary"

const ROLES = ["protagonist", "antagonist", "helper", "rival", "minor", "other"]

const roleBg: Record<string, string> = {
  protagonist: "#4f46e5",
  helper:      "#059669",
  rival:       "#db2777",
  antagonist:  "#dc2626",
}

const inputStyle: React.CSSProperties = {
  width: "100%", boxSizing: "border-box",
  background: "#1a1a24", border: "1px solid #2a2a35", color: "#d1d5db",
  borderRadius: 4, padding: "0.2rem 0.4rem", fontSize: "0.8rem",
}

const panelBtn: React.CSSProperties = {
  background: "none", border: "none", cursor: "pointer",
  padding: "0.1rem 0.25rem", borderRadius: 3,
  display: "flex", alignItems: "center",
}

const labelStyle: React.CSSProperties = {
  fontSize: "0.67rem", opacity: 0.4, marginBottom: "0.1rem",
}

// ── Character card ────────────────────────────────────────────────────────────

interface CharCardProps {
  c: Character
  onSave: (c: Character) => void
  onDelete: () => void
}

function CharCard({ c, onSave, onDelete }: CharCardProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<Character>(c)

  function enterEdit() { setDraft({ ...c }); setEditing(true) }
  function cancel() { setEditing(false) }
  function save() { onSave(draft); setEditing(false) }

  if (editing) {
    return (
      <div style={{ marginBottom: "0.75rem", padding: "0.55rem",
                    background: "rgba(255,255,255,0.04)", borderRadius: 6,
                    border: "1px solid #2a2a35" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>

          <div style={{ display: "flex", gap: "0.4rem" }}>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Name</div>
              <input value={draft.name} style={inputStyle}
                onChange={e => setDraft(d => ({ ...d, name: e.target.value }))} />
            </div>
            <div style={{ width: 100 }}>
              <div style={labelStyle}>Role</div>
              <select value={draft.role} style={{ ...inputStyle, width: "100%" }}
                onChange={e => setDraft(d => ({ ...d, role: e.target.value }))}>
                {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
          </div>

          <div>
            <div style={labelStyle}>Traits (comma-separated)</div>
            <input
              value={draft.traits.join(", ")}
              style={inputStyle}
              onChange={e => setDraft(d => ({
                ...d,
                traits: e.target.value.split(",").map(s => s.trim()).filter(Boolean),
              }))}
            />
          </div>

          <div>
            <div style={labelStyle}>Arc</div>
            <textarea
              value={draft.arc}
              style={{ ...inputStyle, resize: "vertical" as const, minHeight: 48, lineHeight: 1.5 }}
              onChange={e => setDraft(d => ({ ...d, arc: e.target.value }))}
            />
          </div>

          <div>
            <div style={labelStyle}>First appears</div>
            <input value={draft.first_appears ?? ""} style={inputStyle}
              onChange={e => setDraft(d => ({ ...d, first_appears: e.target.value }))} />
          </div>

        </div>

        <div style={{ display: "flex", gap: "0.3rem", marginTop: "0.45rem", justifyContent: "flex-end" }}>
          <button onClick={onDelete}
            style={{ ...panelBtn, color: "#ef4444", gap: "0.2rem", fontSize: "0.72rem" }}>
            <Trash2 size={11} /> Delete
          </button>
          <div style={{ flex: 1 }} />
          <button onClick={cancel} style={{ ...panelBtn, color: "#6b7280", fontSize: "0.72rem" }}>
            Cancel
          </button>
          <button onClick={save}
            style={{ ...panelBtn, color: "#4ade80", gap: "0.2rem", fontSize: "0.72rem" }}>
            <Check size={12} /> Save
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ marginBottom: "0.75rem", padding: "0.6rem",
                  background: "rgba(255,255,255,0.03)", borderRadius: 6 }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.3rem" }}>
        <span style={{ fontWeight: 700, fontSize: "0.88rem", flex: 1 }}>{c.name}</span>
        <span style={{ fontSize: "0.7rem", padding: "0.1rem 0.4rem", borderRadius: 4,
                       background: roleBg[c.role] || "#374151", color: "#fff" }}>
          {c.role}
        </span>
        <button style={{ ...panelBtn, color: "#6b7280" }} onClick={enterEdit} title="Edit character">
          <Pencil size={12} />
        </button>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem", marginBottom: "0.3rem" }}>
        {c.traits.map(t => (
          <span key={t} style={{ fontSize: "0.72rem", padding: "0.1rem 0.35rem",
                                  borderRadius: 3, background: "rgba(255,255,255,0.07)" }}>
            {t}
          </span>
        ))}
      </div>
      {c.arc && <div style={{ fontSize: "0.78rem", opacity: 0.6, fontStyle: "italic" }}>{c.arc}</div>}
    </div>
  )
}

// ── World editor ──────────────────────────────────────────────────────────────

interface WorldEditorProps {
  world: CharacterData["world"]
  onChange: (w: CharacterData["world"]) => void
}

function WorldEditor({ world, onChange }: WorldEditorProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(world)

  function enterEdit() { setDraft({ ...world }); setEditing(true) }
  function save() { onChange(draft); setEditing(false) }

  if (editing) {
    return (
      <div style={{ fontSize: "0.78rem", marginBottom: "0.75rem", padding: "0.45rem",
                    background: "rgba(255,255,255,0.03)", borderRadius: 5,
                    border: "1px solid #2a2a35" }}>
        {(["setting", "time_period", "tone"] as const).map(f => (
          <div key={f} style={{ marginBottom: "0.35rem" }}>
            <div style={labelStyle}>{f.replace("_", " ")}</div>
            <input value={draft[f] ?? ""} style={inputStyle}
              onChange={e => setDraft(d => ({ ...d, [f]: e.target.value }))} />
          </div>
        ))}
        <div style={{ display: "flex", gap: "0.3rem", justifyContent: "flex-end", marginTop: "0.3rem" }}>
          <button style={{ ...panelBtn, color: "#6b7280", fontSize: "0.72rem" }}
            onClick={() => setEditing(false)}>Cancel</button>
          <button style={{ ...panelBtn, color: "#4ade80", fontSize: "0.72rem", gap: "0.2rem" }}
            onClick={save}><Check size={12} /> Save</button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ fontSize: "0.78rem", opacity: 0.5, marginBottom: "0.5rem",
                  display: "flex", alignItems: "center", gap: "0.3rem", cursor: "pointer" }}
      onClick={enterEdit} title="Edit world setting">
      <Globe size={12} />
      <span>{world.setting || "No setting"}</span>
      <Pencil size={10} style={{ opacity: 0.5, marginLeft: "auto" }} />
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function CharacterPanel({ bookName }: { bookName: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["characters", bookName],
    queryFn: () => api.characters(bookName),
    retry: false,
  })
  const saveAll = useUpdateCharacters(bookName)

  function persistWith(patch: Partial<CharacterData>) {
    if (!data) return
    saveAll.mutate({ ...data, ...patch })
  }

  function handleCharSave(i: number, updated: Character) {
    if (!data) return
    const chars = data.characters.map((c, j) => j === i ? updated : c)
    persistWith({ characters: chars })
  }

  function handleCharDelete(i: number) {
    if (!data) return
    persistWith({ characters: data.characters.filter((_, j) => j !== i) })
  }

  function handleAddChar() {
    if (!data) return
    const blank: Character = { name: "New character", role: "minor", traits: [], arc: "", first_appears: "" }
    persistWith({ characters: [...data.characters, blank] })
  }

  function handleWorldChange(world: CharacterData["world"]) {
    persistWith({ world })
  }

  if (isLoading) return <div style={{ padding: "1rem", opacity: 0.4, fontSize: "0.82rem" }}>Loading characters…</div>
  if (isError || !data) return (
    <div style={{ padding: "1rem", opacity: 0.35, fontSize: "0.82rem" }}>
      No character data yet.
    </div>
  )

  return (
    <div style={{ padding: "1rem" }}>
      <div style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.08em",
                    opacity: 0.4, marginBottom: "0.5rem" }}>Characters</div>

      {data.world?.setting !== undefined && (
        <WorldEditor world={data.world} onChange={handleWorldChange} />
      )}

      {data.characters.map((c, i) => (
        <CharCard
          key={i}
          c={c}
          onSave={updated => handleCharSave(i, updated)}
          onDelete={() => handleCharDelete(i)}
        />
      ))}

      <button
        onClick={handleAddChar}
        style={{ ...panelBtn, border: "1px dashed #2a2a35", color: "#6b7280",
                 padding: "0.2rem 0.5rem", fontSize: "0.74rem", gap: "0.3rem",
                 borderRadius: 4, marginTop: "0.25rem" }}>
        <Plus size={12} /> Add character
      </button>
    </div>
  )
}
