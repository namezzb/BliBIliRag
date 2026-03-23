import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import axios from 'axios'
import { useAppStore } from '@/stores/appStore'
import Layout from '@/components/layout/Layout'
import LoginPage from '@/pages/LoginPage'
import VideosPage from '@/pages/VideosPage'
import SearchPage from '@/pages/SearchPage'
import ChatPage from '@/pages/ChatPage'
import TasksPage from '@/pages/TasksPage'
import SettingsPage from '@/pages/SettingsPage'
import '@/styles/globals.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function ProtectedLayout() {
  const [ready, setReady] = useState(false)
  const [authenticated, setAuthenticated] = useState(false)

  useEffect(() => {
    const check = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/auth/me`)
        setAuthenticated(Boolean(response.data?.is_logged_in))
      } catch {
        setAuthenticated(false)
      } finally {
        setReady(true)
      }
    }
    void check()
  }, [])

  if (!ready) {
    return <div className="min-h-screen grid place-items-center text-sm">正在检查登录状态...</div>
  }

  if (!authenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<VideosPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  )
}

function App() {
  const theme = useAppStore((state) => state.theme)

  return (
    <div data-testid="app-root" className={`min-h-screen ${theme === 'dark' ? 'dark' : ''}`}>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/*" element={<ProtectedLayout />} />
        </Routes>
      </Router>
    </div>
  )
}

export default App
