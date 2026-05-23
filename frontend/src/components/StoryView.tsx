import { useState, useCallback, useRef } from "react"
import { Pencil, X } from "lucide-react"
import { useBook, useAnalysis, useUpdateBook } from "../hooks/useLibrary"
import StoryText from "./StoryText"
import EditToolbar from "./EditToolbar"
import MetadataPanel from "./MetadataPanel"
import AnalysisPanel from "./AnalysisPanel"
import CharacterPanel from "./CharacterPanel"

interface Props {
  name: string
  onClose?: () => void
}

const btn: React.CSSProperties = {
  background: "none", border: "1px solid #2a2a35", color: "#9ca3af",
  cursor: "pointer", fontSize: "0.75rem", padding: "0.15rem 0.5rem",
  borderRadius: 4, lineHeight: 1.4,
}

const iconBtn: React.CSSProperties = {
  background: "none", border: "none", cursor: "pointer",
  color: "#9ca3af", padding: "0.2rem 0.3rem", borderRadius: 4,
  display: "flex", alignItems: "center",
}

export default function StoryView({ name, onClose }: Props) {
  const { data: book, isLoading } = useBook(name)
  const { data: analysis } = useAnalysis(name)
  const update = useUpdateBook(name)

  const [metaOpen, setMetaOpen] = useState(true)
  const [editMode, setEditMode] = useState(false)
  const [draft, setDraft] = useState("")

  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const enterEdit = useCallback(() => {
    setDraft(book?.text ?? "")
    setEditMode(true)
  }, [book?.text])

  const cancelEdit = () => setEditMode(false)

  const saveEdit = async () => {
    await update.mutateAsync(draft)
    setEditMode(false)
  }

  if (isLoading) return <div style={{ padding: "2rem", opacity: 0.5 }}>Loading…</div>
  if (!book) return <div style={{ padding: "2rem", opacity: 0.5 }}>Book not found.</div>

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden", background: "#12121a" }}>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem",
                    padding: "0.6rem 1rem", borderBottom: "1px solid #2a2a35", flexShrink: 0 }}>
        <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "#a5b4fc",
                       overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
          {book.classification?.title || name}
        </span>

        {!editMode ? (
          <>
            <button style={iconBtn} onClick={enterEdit} title="Edit text">
              <Pencil size={15} />
            </button>
            <button style={btn} onClick={() => setMetaOpen(o => !o)}>
              {metaOpen ? "Hide info" : "Show info"}
            </button>
          </>
        ) : (
          <>
            <button
              onClick={saveEdit}
              disabled={update.isPending}
              style={{ ...btn, borderColor: "#4f46e5", color: "#a5b4fc",
                       background: "#1e1b4b", opacity: update.isPending ? 0.6 : 1 }}
            >
              {update.isPending ? "Saving…" : "Save"}
            </button>
            <button style={btn} onClick={cancelEdit}>Cancel</button>
          </>
        )}

        {onClose && (
          <button onClick={onClose} style={iconBtn} title="Close">
            <X size={16} />
          </button>
        )}
      </div>

      {/* Edit toolbar — only in edit mode */}
      {editMode && (
        <EditToolbar draft={draft} onChange={setDraft} textareaRef={textareaRef} />
      )}

      {/* Body */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
          <StoryText
            ref={textareaRef}
            text={editMode ? draft : book.text}
            editMode={editMode}
            onChange={setDraft}
          />
        </div>

        {metaOpen && !editMode && (
          <div style={{ width: 260, flexShrink: 0, borderLeft: "1px solid #2a2a35",
                        overflowY: "auto", background: "#16161d" }}>
            <MetadataPanel bookName={name} classification={book.classification} pipeline={book.pipeline} />
            <div style={{ borderTop: "1px solid #2a2a35" }}>
              <AnalysisPanel bookName={name} analysis={analysis} />
            </div>
            <div style={{ borderTop: "1px solid #2a2a35" }}>
              <CharacterPanel bookName={name} />
            </div>
          </div>
        )}
      </div>

    </div>
  )
}
