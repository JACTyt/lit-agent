import { useRef, useCallback } from "react"
import Sidebar from "./Sidebar"
import ChatView from "./ChatView"
import StoryView from "./StoryView"
import { useLocalState } from "../hooks/useLocalState"

const SIDEBAR_MIN = 160
const SIDEBAR_MAX = 400
const CENTER_MIN = 280
const CENTER_MAX = 860
const CHAT_MIN = 320

function useDragHandle(onDelta: (dx: number) => void) {
  const lastX = useRef(0)

  return useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    lastX.current = e.clientX

    const onMove = (ev: MouseEvent) => {
      const dx = ev.clientX - lastX.current
      lastX.current = ev.clientX
      onDelta(dx)
    }
    const onUp = () => {
      window.removeEventListener("mousemove", onMove)
      window.removeEventListener("mouseup", onUp)
    }
    window.addEventListener("mousemove", onMove)
    window.addEventListener("mouseup", onUp)
  }, [onDelta])
}

const handleBar: React.CSSProperties = {
  width: 5,
  flexShrink: 0,
  cursor: "col-resize",
  background: "transparent",
  transition: "background 0.15s",
  zIndex: 10,
}

const collapseBtn: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "#6b7280",
  cursor: "pointer",
  fontSize: "0.8rem",
  padding: "0.2rem 0.35rem",
  lineHeight: 1,
  borderRadius: 4,
}

export default function Layout() {
  const [selectedBook, setSelectedBook] = useLocalState<string | null>("layout.selectedBook", null)
  const [sidebarW, setSidebarW] = useLocalState<number>("layout.sidebarW", 220)
  const [centerW, setCenterW] = useLocalState<number>("layout.centerW", 480)
  const [sidebarOpen, setSidebarOpen] = useLocalState<boolean>("layout.sidebarOpen", true)

  const dragSidebar = useDragHandle(useCallback((dx) => {
    setSidebarW(w => Math.max(SIDEBAR_MIN, Math.min(SIDEBAR_MAX, w + dx)))
  }, []))

  const dragCenter = useDragHandle(useCallback((dx) => {
    setCenterW(w => Math.max(CENTER_MIN, Math.min(CENTER_MAX, w + dx)))
  }, []))

  const selectBook = useCallback((name: string | null) => setSelectedBook(name), [])

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "#0f0f17", color: "#e5e7eb" }}>

      {/* Sidebar — collapsed strip or full panel */}
      {sidebarOpen ? (
        <>
          <div style={{ width: sidebarW, flexShrink: 0, overflow: "hidden" }}>
            <Sidebar
              selectedBook={selectedBook}
              onSelectBook={selectBook}
              onCollapse={() => setSidebarOpen(false)}
            />
          </div>
          <div
            style={handleBar}
            onMouseDown={dragSidebar}
            onMouseEnter={e => (e.currentTarget.style.background = "#4f46e5")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
          />
        </>
      ) : (
        <div style={{ width: 28, flexShrink: 0, background: "#16161d",
                      borderRight: "1px solid #2a2a35", display: "flex",
                      flexDirection: "column", alignItems: "center", paddingTop: "0.5rem" }}>
          <button
            style={collapseBtn}
            title="Show sidebar"
            onClick={() => setSidebarOpen(true)}
          >▶</button>
        </div>
      )}

      {/* Center: book panel */}
      {selectedBook && (
        <>
          <div style={{ width: centerW, flexShrink: 0, overflow: "hidden", borderLeft: "1px solid #2a2a35" }}>
            <StoryView name={selectedBook} onClose={() => setSelectedBook(null)} />
          </div>
          <div
            style={handleBar}
            onMouseDown={dragCenter}
            onMouseEnter={e => (e.currentTarget.style.background = "#4f46e5")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
          />
        </>
      )}

      {/* Chat — always visible, fills remaining space */}
      <div style={{ flex: 1, minWidth: CHAT_MIN, overflow: "hidden", borderLeft: "1px solid #2a2a35" }}>
        <ChatView />
      </div>
    </div>
  )
}
