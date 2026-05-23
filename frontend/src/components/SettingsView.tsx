import { useQuery } from "@tanstack/react-query"
import { api } from "../api"

export default function SettingsView() {
  const { data } = useQuery({ queryKey: ["health"], queryFn: api.health })
  return (
    <div style={{ padding: "2rem" }}>
      <h2 style={{ marginBottom: "1rem" }}>Settings</h2>
      {data && (
        <table style={{ borderCollapse: "collapse", fontSize: "0.9rem" }}>
          <tbody>
            {Object.entries(data).map(([k, v]) => (
              <tr key={k}>
                <td style={{ padding: "0.3rem 1rem 0.3rem 0", opacity: 0.5 }}>{k}</td>
                <td style={{ fontFamily: "monospace" }}>{String(v)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
