import { useQuery } from "@tanstack/react-query"
import { api, Character } from "../api"

const roleBg: Record<string, string> = {
  protagonist: "#4f46e5",
  helper: "#059669",
  rival: "#db2777",
  antagonist: "#dc2626",
}

function CharCard({ c }: { c: Character }) {
  return (
    <div style={{ marginBottom: "0.75rem", padding: "0.6rem",
                  background: "rgba(255,255,255,0.03)", borderRadius: 6 }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.3rem" }}>
        <span style={{ fontWeight: 700, fontSize: "0.88rem" }}>{c.name}</span>
        <span style={{ fontSize: "0.7rem", padding: "0.1rem 0.4rem", borderRadius: 4,
                       background: roleBg[c.role] || "#374151", color: "#fff" }}>
          {c.role}
        </span>
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

export default function CharacterPanel({ bookName }: { bookName: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["characters", bookName],
    queryFn: () => api.characters(bookName),
    retry: false,
  })

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
      {data.world?.setting && (
        <div style={{ fontSize: "0.78rem", opacity: 0.5, marginBottom: "0.5rem" }}>
          🌍 {data.world.setting}
        </div>
      )}
      {data.characters.map(c => <CharCard key={c.name} c={c} />)}
      <div style={{ fontSize: "0.72rem", opacity: 0.3, marginTop: "0.5rem" }}>
        Direct editing → v2.1
      </div>
    </div>
  )
}
