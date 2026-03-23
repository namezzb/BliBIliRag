import { create } from 'zustand'
import { Task } from '@/services/api'

export interface Conversation {
  id: string
  title: string
  messages: Array<{ role: 'user' | 'assistant'; content: string }>
  createdAt: number
}

interface AppStore {
  // User state
  user: { id: string; name: string } | null
  setUser: (user: { id: string; name: string } | null) => void

  // Search state
  searchHistory: string[]
  addSearchHistory: (query: string) => void
  clearSearchHistory: () => void

  // Conversation state
  conversations: Conversation[]
  currentConversation: Conversation | null
  setCurrentConversation: (conv: Conversation | null) => void
  addConversation: (conv: Conversation) => void
  deleteConversation: (id: string) => void

  // Task state
  tasks: Task[]
  setTasks: (tasks: Task[]) => void
  updateTask: (task: Task) => void

  // UI state
  theme: 'light' | 'dark'
  setTheme: (theme: 'light' | 'dark') => void
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
}

export const useAppStore = create<AppStore>((set) => ({
  // User state
  user: null,
  setUser: (user) => set({ user }),

  // Search state
  searchHistory: [],
  addSearchHistory: (query) =>
    set((state) => ({
      searchHistory: [query, ...state.searchHistory.filter((q) => q !== query)].slice(0, 20),
    })),
  clearSearchHistory: () => set({ searchHistory: [] }),

  // Conversation state
  conversations: [],
  currentConversation: null,
  setCurrentConversation: (conv) => set({ currentConversation: conv }),
  addConversation: (conv) =>
    set((state) => ({
      conversations: [conv, ...state.conversations],
    })),
  deleteConversation: (id) =>
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      currentConversation: state.currentConversation?.id === id ? null : state.currentConversation,
    })),

  // Task state
  tasks: [],
  setTasks: (tasks) => set({ tasks }),
  updateTask: (task) =>
    set((state) => ({
      tasks: state.tasks.map((t) => (t.task_id === task.task_id ? task : t)),
    })),

  // UI state
  theme: 'light',
  setTheme: (theme) => set({ theme }),
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}))
