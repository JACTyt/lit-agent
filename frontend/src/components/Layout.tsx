import { ReactNode } from "react"
import Sidebar from "./Sidebar"

const styles: Record<string, React.CSSProperties> = {
  root: { display: "flex", height: "100vh", overflow: "hidden" },
  main: { flex: 1, overflow: "auto", display: "flex", flexDirection: "column" },
}

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div style={styles.root}>
      <Sidebar />
      <main style={styles.main}>{children}</main>
    </div>
  )
}
