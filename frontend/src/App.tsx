import { Routes, Route } from "react-router-dom"
import Layout from "./components/Layout"
import ChatView from "./components/ChatView"
import StoryView from "./components/StoryView"
import SettingsView from "./components/SettingsView"

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<ChatView />} />
        <Route path="/library/:name" element={<StoryView />} />
        <Route path="/settings" element={<SettingsView />} />
      </Routes>
    </Layout>
  )
}
