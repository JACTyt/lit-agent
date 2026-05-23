import { useParams } from "react-router-dom"
import { useBook, useAnalysis } from "../hooks/useLibrary"
import StoryText from "./StoryText"
import MetadataPanel from "./MetadataPanel"
import AnalysisPanel from "./AnalysisPanel"
import CharacterPanel from "./CharacterPanel"

export default function StoryView() {
  const { name } = useParams<{ name: string }>()
  const { data: book, isLoading } = useBook(name!)
  const { data: analysis } = useAnalysis(name!)

  if (isLoading) return <div style={{ padding: "2rem", opacity: 0.5 }}>Loading…</div>
  if (!book) return <div style={{ padding: "2rem", opacity: 0.5 }}>Book not found.</div>

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      <div style={{ flex: 1, overflowY: "auto" }}>
        <StoryText text={book.text} />
      </div>
      <aside style={{ width: 280, borderLeft: "1px solid #2a2a35", overflowY: "auto",
                      background: "#16161d" }}>
        <MetadataPanel classification={book.classification} pipeline={book.pipeline} />
        <AnalysisPanel analysis={analysis} />
        <CharacterPanel bookName={name!} />
      </aside>
    </div>
  )
}
