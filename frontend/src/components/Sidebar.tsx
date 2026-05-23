import { Link, useLocation } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { api, BookSummary } from "../api"

const s: Record<string, React.CSSProperties> = {
  sidebar: { width: 220, background: "#16161d", borderRight: "1px solid #2a2a35",
             display: "flex", flexDirection: "column", padding: "0.75rem 0" },
  title: { padding: "0 1rem 0.75rem", fontWeight: 700, fontSize: "1rem", color: "#818cf8",
           borderBottom: "1px solid #2a2a35", marginBottom: "0.5rem" },
  label: { padding: "0.25rem 1rem", fontSize: "0.7rem", textTransform: "uppercase",
           letterSpacing: "0.08em", opacity: 0.4, marginTop: "0.5rem" },
  item: { padding: "0.4rem 1rem", fontSize: "0.85rem", cursor: "pointer",
          textDecoration: "none", color: "#e5e7eb", display: "block", borderRadius: 4,
          margin: "0 0.25rem" },
  footer: { marginTop: "auto", padding: "0.75rem 1rem", fontSize: "0.75rem", opacity: 0.4,
            borderTop: "1px solid #2a2a35" },
}

export default function Sidebar() {
  const { data: books = [] } = useQuery({ queryKey: ["library"], queryFn: api.library })
  const { data: health } = useQuery({ queryKey: ["health"], queryFn: api.health })
  const loc = useLocation()

  return (
    <aside style={s.sidebar}>
      <div style={s.title}>📚 LitBot</div>
      <Link to="/" style={{ ...s.item, background: loc.pathname === "/" ? "#1e1e2e" : "transparent" }}>
        💬 Chat
      </Link>
      <Link to="/settings" style={{ ...s.item, background: loc.pathname === "/settings" ? "#1e1e2e" : "transparent" }}>
        ⚙️ Settings
      </Link>
      <div style={s.label}>Library</div>
      {books.map((b: BookSummary) => (
        <Link
          key={b.book_name}
          to={`/library/${b.book_name}`}
          style={{ ...s.item, background: loc.pathname === `/library/${b.book_name}` ? "#1e1e2e" : "transparent" }}
        >
          📖 {b.classification?.title || b.book_name}
        </Link>
      ))}
      <div style={s.footer}>
        {health ? `${health.provider} · ${health.model}` : "…"}
      </div>
    </aside>
  )
}
