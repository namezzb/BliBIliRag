import { ReactNode } from 'react'
import { useAppStore } from '@/stores/appStore'
import Sidebar from './Sidebar'
import Header from './Header'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const sidebarOpen = useAppStore((state) => state.sidebarOpen)

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />

        <main className="flex-1 overflow-auto">
          <div
            className={`mx-auto w-full max-w-[1600px] px-4 pb-6 pt-5 sm:px-6 lg:px-8 transition-all duration-200 ${
              sidebarOpen ? '' : 'max-w-[1680px]'
            }`}
          >
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
