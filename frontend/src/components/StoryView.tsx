import { useState } from "react"
import { useBook, useAnalysis } from "../hooks/useLibrary"
import StoryText from "./StoryText"
import MetadataPanel from "./MetadataPanel"
import AnalysisPanel from "./AnalysisPanel"
import CharacterPanel from "./CharacterPanel"

interface Props {
  name: string
  onClose?: () => void
}

const btnStyle: React.CSSProperties = {
  background: "none", border: "1px solid #2a2a35", color: "#9ca3af",
  cursor: "pointer", fontSize: "0.75rem", padding: "0.15rem 0.5rem",
  borderRadius: 4, lineHeight: 1.4,
}

export default function StoryView({ name, onClose }: Props) {
  const { data: book, isLoading } = useBook(name)
  const { data: analysis } = useAnalysis(name)
  const [metaOpen, setMetaOpen] = useState(true)

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
        <button style={btnStyle} onClick={() => setMetaOpen(o => !o)}>
          {metaOpen ? "Hide info" : "Show info"}
        </button>
        {onClose && (
          <button
            onClick={onClose}
            style={{ ...btnStyle, border: "none", color: "#6b7280", fontSize: "1rem", padding: "0 0.2rem" }}
          >
            ✕
          </button>
        )}
      </div>

      {/* Body: text left, meta panel right */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Story text */}
        <div style={{ flex: 1, overflowY: "auto" }}>
          <StoryText text={book.text} />
        </div>

        {/* Collapsible meta/analysis/characters panel */}
        {metaOpen && (
          <div style={{ width: 260, flexShrink: 0, borderLeft: "1px solid #2a2a35",
                        overflowY: "auto", background: "#16161d" }}>
            <MetadataPanel classification={book.classification} pipeline={book.pipeline} />
            <div style={{ borderTop: "1px solid #2a2a35" }}>
              <AnalysisPanel analysis={analysis} />
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
