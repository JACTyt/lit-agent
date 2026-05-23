import { Classification, PipelineMeta } from "../api"

interface Props { classification?: Partial<Classification>; pipeline?: PipelineMeta }

export default function MetadataPanel({ classification = {}, pipeline }: Props) {
  const rows = Object.entries(classification).filter(([, v]) => v)
  return (
    <div style={{ padding: "1rem", borderBottom: "1px solid #2a2a35" }}>
      <div style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.08em",
                    opacity: 0.4, marginBottom: "0.5rem" }}>Metadata</div>
      <table style={{ borderCollapse: "collapse", fontSize: "0.82rem", width: "100%" }}>
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k}>
              <td style={{ padding: "0.2rem 0.5rem 0.2rem 0", opacity: 0.5, whiteSpace: "nowrap" }}>{k}</td>
              <td style={{ padding: "0.2rem 0" }}>{String(v)}</td>
            </tr>
          ))}
          {pipeline?.critic_score !== undefined && (
            <tr>
              <td style={{ padding: "0.2rem 0.5rem 0.2rem 0", opacity: 0.5 }}>critic score</td>
              <td>{pipeline.critic_score.toFixed(2)}</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
