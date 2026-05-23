import { useQuery } from "@tanstack/react-query"
import { api, BookSummary } from "../api"

interface Props {
  selectedBook: string | null
  onSelectBook: (name: string | null) => void
  onCollapse: () => void
}

const s: Record<string, React.CSSProperties> = {
  sidebar: { width: "100%", height: "100%", background: "#16161d", borderRight: "1px solid #2a2a35",
             display: "flex", flexDirection: "column", padding: "0.75rem 0", overflow: "hidden" },
  header: { display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "0 1rem 0.75rem", borderBottom: "1px solid #2a2a35", marginBottom: "0.5rem",
            flexShrink: 0 },
  title: { fontWeight: 700, fontSize: "1rem", color: "#818cf8" },
  label: { padding: "0.25rem 1rem", fontSize: "0.7rem", textTransform: "uppercase" as const,
           letterSpacing: "0.08em", opacity: 0.4, marginTop: "0.5rem", flexShrink: 0 },
  bookList: { overflowY: "auto" as const, flex: 1 },
  item: { padding: "0.4rem 1rem", fontSize: "0.85rem", cursor: "pointer",
          color: "#e5e7eb", display: "block", borderRadius: 4,
          margin: "0 0.25rem", background: "none", border: "none",
          width: "calc(100% - 0.5rem)", textAlign: "left" as const },
  footer: { marginTop: "auto", padding: "0.75rem 1rem", fontSize: "0.75rem", opacity: 0.4,
            borderTop: "1px solid #2a2a35", flexShrink: 0 },
  collapseBtn: { background: "none", border: "none", color: "#6b7280", cursor: "pointer",
                 fontSize: "0.8rem", padding: "0.1rem 0.3rem", lineHeight: 1, borderRadius: 3 },
}

export default function Sidebar({ selectedBook, onSelectBook, onCollapse }: Props) {
  const { data: books = [] } = useQuery({ queryKey: ["library"], queryFn: api.library })
  const { data: health } = useQuery({ queryKey: ["health"], queryFn: api.health })

  return (
    <aside style={s.sidebar}>
      <div style={s.header}>
        <span style={s.title}>📚 LitBot</span>
        <button style={s.collapseBtn} title="Hide sidebar" onClick={onCollapse}>◀</button>
      </div>
      <div style={s.label}>Library</div>
      <div style={s.bookList}>
        {books.map((b: BookSummary) => (
          <button
            key={b.book_name}
            style={{
              ...s.item,
              background: selectedBook === b.book_name ? "#1e1e2e" : "transparent",
              color: selectedBook === b.book_name ? "#a5b4fc" : "#e5e7eb",
            }}
            onClick={() => onSelectBook(selectedBook === b.book_name ? null : b.book_name)}
          >
            📖 {b.classification?.title || b.book_name}
          </button>
        ))}
      </div>
      <div style={s.footer}>
        {health ? `${health.provider} · ${health.model}` : "…"}
      </div>
    </aside>
  )
}
