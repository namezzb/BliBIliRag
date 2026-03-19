import { useState } from 'react'
import { apiClient, SearchResult } from '@/services/api'
import { useAppStore } from '@/stores/appStore'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [routingStrategy, setRoutingStrategy] = useState('hybrid')

  const searchHistory = useAppStore((state) => state.searchHistory)
  const addSearchHistory = useAppStore((state) => state.addSearchHistory)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    try {
      setLoading(true)
      setError(null)
      addSearchHistory(query)
      const data = await apiClient.search(query, 5, routingStrategy)
      setResults(data.results)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">智能搜索</h2>

      {/* Search form */}
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入搜索关键词..."
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '搜索中...' : '搜索'}
          </button>
        </div>

        {/* Routing strategy */}
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">路由策略:</label>
          <select
            value={routingStrategy}
            onChange={(e) => setRoutingStrategy(e.target.value)}
            className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="logical">逻辑路由</option>
            <option value="semantic">语义路由</option>
            <option value="hybrid">混合路由</option>
            <option value="direct">直接路由</option>
          </select>
        </div>
      </form>

      {/* Search history */}
      {searchHistory.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">搜索历史:</p>
          <div className="flex flex-wrap gap-2">
            {searchHistory.slice(0, 5).map((item, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setQuery(item)
                  // Trigger search
                }}
                className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="p-4 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg">
          {error}
        </div>
      )}

      {/* Results */}
      <div className="space-y-4">
        {results.length === 0 && !loading && query && (
          <div className="text-center py-12 text-gray-500">暂无搜索结果</div>
        )}

        {results.map((result, idx) => (
          <div
            key={idx}
            className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 dark:text-white">{result.title}</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">{result.content}</p>
                <div className="flex items-center gap-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
                  <span>BV: {result.bvid}</span>
                  <span>相关度: {(result.relevance_score * 100).toFixed(0)}%</span>
                </div>
              </div>
              <button className="ml-4 px-3 py-1 text-sm bg-primary text-white rounded hover:bg-blue-700 transition-colors">
                查看
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
