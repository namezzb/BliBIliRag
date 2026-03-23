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
    <div data-testid="search-page" className="space-y-6 animate-fade-in">
      <section className="panel p-5 sm:p-6">
        <h2 className="text-3xl font-bold" style={{ color: 'var(--text-main)' }}>
          智能搜索控制台
        </h2>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-subtle)' }}>
          基于 RAG 路由策略查询视频内容，支持语义与逻辑混合检索。
        </p>
      </section>

      <section className="panel p-5 sm:p-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="flex flex-col gap-3 md:flex-row">
            <input
              data-testid="search-input"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="输入搜索关键词..."
              className="input-base"
            />
            <button data-testid="search-submit" type="submit" disabled={loading} className="btn-primary md:w-44">
              {loading ? '搜索中...' : '执行搜索'}
            </button>
          </div>

          <div className="panel-muted p-4">
            <label className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-subtle)' }}>
              Routing Strategy
            </label>
            <select
              value={routingStrategy}
              onChange={(e) => setRoutingStrategy(e.target.value)}
              className="input-base mt-2"
            >
              <option value="logical">逻辑路由</option>
              <option value="semantic">语义路由</option>
              <option value="hybrid">混合路由</option>
              <option value="direct">直接路由</option>
            </select>
          </div>

          {searchHistory.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {searchHistory.slice(0, 6).map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setQuery(item)}
                  className="badge-primary transition hover:opacity-80"
                >
                  {item}
                </button>
              ))}
            </div>
          )}
        </form>
      </section>

      {error && (
        <section className="panel p-4 text-sm" style={{ color: '#a92929', borderColor: '#f5bcbc', background: '#fff1f1' }}>
          {error}
        </section>
      )}

      <section data-testid="search-results" className="space-y-4">
        {loading ? (
          <div className="panel p-8 text-sm" style={{ color: 'var(--text-subtle)' }}>
            正在拉取检索结果...
          </div>
        ) : results.length === 0 && query ? (
          <div className="panel p-8 text-center">
            <p className="font-semibold" style={{ color: 'var(--text-main)' }}>
              暂无搜索结果
            </p>
            <p className="mt-2 text-sm" style={{ color: 'var(--text-subtle)' }}>
              可尝试换一个关键词或更改路由策略。
            </p>
          </div>
        ) : (
          results.map((result, idx) => (
            <article key={`${result.bvid}-${idx}`} className="card p-5 animate-slide-up">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate text-lg font-semibold" style={{ color: 'var(--text-main)' }}>
                    {result.title}
                  </h3>
                  <p className="mt-2 text-sm leading-6" style={{ color: 'var(--text-subtle)' }}>
                    {result.content}
                  </p>
                </div>
                <span className="badge-primary shrink-0">{Math.round(result.relevance_score * 100)}%</span>
              </div>
              <div className="mt-3 flex items-center gap-2 text-xs" style={{ color: 'var(--text-subtle)' }}>
                <span className="badge">BV {result.bvid}</span>
                <span>{result.source}</span>
              </div>
            </article>
          ))
        )}
      </section>
    </div>
  )
}
