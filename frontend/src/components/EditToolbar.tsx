import { useState, RefObject } from "react"
import {
  Undo2, ArrowRight, Eraser, WrapText, AlignJustify,
  Quote, Minus, Ellipsis, WholeWord, SeparatorHorizontal,
  Replace,
} from "lucide-react"

interface Props {
  draft: string
  onChange: (text: string) => void
  textareaRef: RefObject<HTMLTextAreaElement | null>
}

// ── styles ──────────────────────────────────────────────────────────────────

const toolBtn: React.CSSProperties = {
  background: "none", border: "1px solid #2a2a35", color: "#9ca3af",
  cursor: "pointer", fontSize: "0.74rem", padding: "0.18rem 0.45rem",
  borderRadius: 4, lineHeight: 1.4, whiteSpace: "nowrap",
  display: "flex", alignItems: "center", gap: "0.3rem",
}

const inputStyle: React.CSSProperties = {
  background: "#1a1a24", border: "1px solid #2a2a35", color: "#d1d5db",
  borderRadius: 4, padding: "0.2rem 0.5rem", fontSize: "0.8rem",
}

const sep: React.CSSProperties = {
  width: 1, height: 14, background: "#2a2a35", flexShrink: 0, margin: "0 0.1rem",
}

const rowStyle: React.CSSProperties = {
  display: "flex", alignItems: "center", gap: "0.35rem", flexWrap: "wrap",
  padding: "0.42rem 1rem", background: "#0e0e16", flexShrink: 0,
}

// ── transforms ──────────────────────────────────────────────────────────────

function fixSpacing(text: string): string {
  return text
    .split("\n")
    .map(line => line.replace(/ {2,}/g, " ").trimEnd())
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
}

function applySmartQuotes(text: string): string {
  return text
    .replace(/(^|[\s([{])"(?=\S)/gm, "$1“")
    .replace(/"/g, "”")
    .replace(/(\w)'(\w)/g, "$1’$2")
    .replace(/(^|[\s([{])'(?=\S)/gm, "$1‘")
    .replace(/'/g, "’")
}

function applyEmDashes(text: string): string {
  return text.replace(/\s*--\s*/g, m => m.includes(" ") ? " — " : "—")
}

function applyEllipsis(text: string): string {
  return text.replace(/\.{3}/g, "…")
}

function capitalizeSentences(text: string): string {
  return text
    .replace(/^([a-z])/, c => c.toUpperCase())
    .replace(/([.!?]\s+)([a-z])/g, (_, p, c) => p + c.toUpperCase())
}

function stripTrailingSpaces(text: string): string {
  return text.split("\n").map(l => l.trimEnd()).join("\n")
}

function normalizeLineBreaks(text: string): string {
  return text
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim()
}

// ── component ────────────────────────────────────────────────────────────────

export default function EditToolbar({ draft, onChange, textareaRef }: Props) {
  const [prevDraft, setPrevDraft] = useState<string | null>(null)
  const [findVal, setFindVal] = useState("")
  const [replaceVal, setReplaceVal] = useState("")
  const [caseSensitive, setCaseSensitive] = useState(false)
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null)

  const words = draft.trim() ? draft.trim().split(/\s+/).length : 0
  const chars = draft.length
  const paragraphs = draft.split(/\n{2,}/).filter(p => p.trim()).length

  function applyTransform(fn: (t: string) => string, label: string) {
    const next = fn(draft)
    if (next === draft) { setMsg({ text: "No changes", ok: false }); return }
    setPrevDraft(draft)
    onChange(next)
    setMsg({ text: label, ok: true })
  }

  function handleUndo() {
    if (prevDraft === null) return
    onChange(prevDraft)
    setPrevDraft(null)
    setMsg({ text: "Undone", ok: true })
  }

  function handleSceneBreak() {
    const el = textareaRef.current
    const pos = el?.selectionStart ?? draft.length
    const ins = "\n\n* * *\n\n"
    const next = draft.slice(0, pos) + ins + draft.slice(pos)
    setPrevDraft(draft)
    onChange(next)
    setMsg({ text: "Scene break inserted", ok: true })
    requestAnimationFrame(() => {
      if (el) { el.selectionStart = el.selectionEnd = pos + ins.length; el.focus() }
    })
  }

  function handleReplaceAll() {
    if (!findVal) return
    const flags = caseSensitive ? "g" : "gi"
    let pat: RegExp
    try {
      pat = new RegExp(findVal.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), flags)
    } catch { return }
    let count = 0
    const next = draft.replace(pat, () => { count++; return replaceVal })
    if (count) { setPrevDraft(draft); onChange(next) }
    setMsg(count > 0
      ? { text: `Replaced ${count} occurrence${count !== 1 ? "s" : ""}`, ok: true }
      : { text: "No matches", ok: false })
  }

  return (
    <div style={{ borderBottom: "1px solid #2a2a35" }}>

      {/* ── Row 1: smart tools ── */}
      <div style={rowStyle}>
        <button style={toolBtn} title="Collapse double spaces, trim line ends, fold 3+ blank lines into 1"
          onClick={() => applyTransform(fixSpacing, "Spacing fixed")}>
          <Eraser size={13} /> Fix spaces
        </button>
        <button style={toolBtn} title="CRLF→LF, collapse excess blank lines, trim document edges"
          onClick={() => applyTransform(normalizeLineBreaks, "Line breaks normalized")}>
          <WrapText size={13} /> Norm. breaks
        </button>
        <button style={toolBtn} title="Strip trailing whitespace from every line"
          onClick={() => applyTransform(stripTrailingSpaces, "Trailing spaces stripped")}>
          <AlignJustify size={13} /> Trim lines
        </button>

        <div style={sep} />

        <button style={toolBtn} title='Convert straight "quotes" to typographic “curly” quotes'
          onClick={() => applyTransform(applySmartQuotes, "Smart quotes applied")}>
          <Quote size={13} /> Quotes
        </button>
        <button style={toolBtn} title="Convert -- to em dash (—)"
          onClick={() => applyTransform(applyEmDashes, "Em dashes applied")}>
          <Minus size={13} /> Em dashes
        </button>
        <button style={toolBtn} title="Convert ... to ellipsis character (…)"
          onClick={() => applyTransform(applyEllipsis, "Ellipses applied")}>
          <Ellipsis size={13} /> Ellipsis
        </button>
        <button style={toolBtn} title="Capitalize first letter after every sentence-ending punctuation"
          onClick={() => applyTransform(capitalizeSentences, "Sentences capitalized")}>
          <WholeWord size={13} /> Cap sentences
        </button>

        <div style={sep} />

        <button style={toolBtn} title="Insert '* * *' scene break at cursor position"
          onClick={handleSceneBreak}>
          <SeparatorHorizontal size={13} /> Scene break
        </button>

        <div style={sep} />

        <button
          onClick={handleUndo}
          disabled={prevDraft === null}
          style={{ ...toolBtn, opacity: prevDraft === null ? 0.3 : 1 }}
          title="Undo last smart-tool transform (single level)"
        >
          <Undo2 size={13} /> Undo
        </button>

        {msg && (
          <span style={{ fontSize: "0.71rem", color: msg.ok ? "#4ade80" : "#f87171", marginLeft: 2 }}>
            {msg.text}
          </span>
        )}

        <div style={{ flex: 1 }} />
        <span style={{ fontSize: "0.71rem", color: "#374151", whiteSpace: "nowrap" }}>
          {words.toLocaleString()} words &middot; {chars.toLocaleString()} chars &middot; {paragraphs} para
        </span>
      </div>

      {/* ── Row 2: find & replace ── */}
      <div style={{ ...rowStyle, borderTop: "1px solid #181820" }}>
        <Replace size={13} style={{ color: "#4b5563", flexShrink: 0 }} />
        <input
          placeholder="Find…"
          value={findVal}
          onChange={e => { setFindVal(e.target.value); setMsg(null) }}
          onKeyDown={e => e.key === "Enter" && handleReplaceAll()}
          style={{ ...inputStyle, width: 150 }}
        />
        <ArrowRight size={13} style={{ color: "#374151", flexShrink: 0 }} />
        <input
          placeholder="Replace with…"
          value={replaceVal}
          onChange={e => setReplaceVal(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleReplaceAll()}
          style={{ ...inputStyle, width: 150 }}
        />
        <label style={{ display: "flex", alignItems: "center", gap: "0.25rem",
                        color: "#6b7280", fontSize: "0.74rem", cursor: "pointer", userSelect: "none" }}>
          <input type="checkbox" checked={caseSensitive}
            onChange={e => setCaseSensitive(e.target.checked)} style={{ accentColor: "#4f46e5" }} />
          Aa
        </label>
        <button onClick={handleReplaceAll} style={toolBtn}>Replace all</button>
      </div>

    </div>
  )
}
