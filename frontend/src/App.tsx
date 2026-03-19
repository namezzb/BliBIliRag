import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useAppStore } from '@/stores/appStore'
import Layout from '@/components/layout/Layout'
import VideosPage from '@/pages/VideosPage'
import SearchPage from '@/pages/SearchPage'
import ChatPage from '@/pages/ChatPage'
import TasksPage from '@/pages/TasksPage'
import SettingsPage from '@/pages/SettingsPage'
import '@/styles/globals.css'

function App() {
  const theme = useAppStore((state) => state.theme)

  return (
    <div className={theme === 'dark' ? 'dark' : ''}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<VideosPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </Layout>
      </Router>
    </div>
  )
}

export default App
