import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { apiClient, FavoriteFolder, Video } from '@/services/api'

export default function VideosPage() {
  const navigate = useNavigate()
  const [favorites, setFavorites] = useState<FavoriteFolder[]>([])
  const [selectedFolders, setSelectedFolders] = useState<number[]>([])
  const [videos, setVideos] = useState<Video[]>([])
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const [loading, setLoading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const limit = 20

  useEffect(() => {
    void loadData()
  }, [skip])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [favoritesData, videosData] = await Promise.all([
        apiClient.getFavorites(),
        apiClient.getVideos(skip, limit),
      ])
      setFavorites(favoritesData)
      setVideos(videosData.videos)
      setTotal(videosData.total)
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        navigate('/login')
        return
      }
      setError(err instanceof Error ? err.message : 'Failed to load videos')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (bvid: string) => {
    if (!confirm('确定要删除这个视频吗？')) return

    try {
      await apiClient.deleteVideo(bvid)
      setVideos(videos.filter((v) => v.bvid !== bvid))
      setTotal(total - 1)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete video')
    }
  }

  const handleImport = async () => {
    if (selectedFolders.length === 0) {
      setError('请先选择至少一个收藏夹')
      return
    }
    try {
      setImporting(true)
      setError(null)
      const result = await apiClient.importFavorites(selectedFolders)
      alert(`导入完成：扫描 ${result.scanned} 条，新增 ${result.imported} 条`)
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import videos')
    } finally {
      setImporting(false)
    }
  }

  const toggleFolder = (folderId: number) => {
    setSelectedFolders((prev) =>
      prev.includes(folderId) ? prev.filter((id) => id !== folderId) : [...prev, folderId]
    )
  }

  return (
    <div data-testid="videos-page" className="space-y-6 animate-fade-in">
      <section className="panel p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-3xl font-bold" style={{ color: 'var(--text-main)' }}>
              视频库控制台
            </h2>
            <p className="mt-2 text-sm" style={{ color: 'var(--text-subtle)' }}>
              管理收藏视频、触发导入任务并追踪内容索引状态。
            </p>
          </div>
          <button data-testid="videos-import-btn" onClick={handleImport} disabled={importing} className="btn-primary">
            {importing ? '导入中...' : '导入选中收藏夹'}
          </button>
        </div>
      </section>

      <section className="panel p-5 sm:p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-semibold" style={{ color: 'var(--text-main)' }}>
            可导入收藏夹
          </h3>
          <span className="text-sm" style={{ color: 'var(--text-subtle)' }}>
            已选 {selectedFolders.length} 个
          </span>
        </div>
        <div className="mt-4 space-y-2">
          {favorites.length === 0 ? (
            <p className="text-sm" style={{ color: 'var(--text-subtle)' }}>
              当前账号下未获取到收藏夹
            </p>
          ) : (
            favorites.map((folder) => (
              <label
                key={folder.id}
                className="panel-muted flex cursor-pointer items-center justify-between rounded-xl px-4 py-3 text-sm"
              >
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={selectedFolders.includes(folder.id)}
                    onChange={() => toggleFolder(folder.id)}
                  />
                  <span style={{ color: 'var(--text-main)' }}>
                    {folder.title}
                    {folder.is_default ? '（默认）' : ''}
                  </span>
                </div>
                <span style={{ color: 'var(--text-subtle)' }}>{folder.media_count} 条</span>
              </label>
            ))
          )}
        </div>
      </section>

      {error && (
        <div className="panel p-4 text-sm" style={{ color: '#a92929', borderColor: '#f5bcbc', background: '#fff1f1' }}>
          {error}
        </div>
      )}

      {loading ? (
        <div className="panel p-10 text-center">
          <div className="inline-flex items-center gap-2 text-sm" style={{ color: 'var(--text-subtle)' }}>
            <span className="h-2.5 w-2.5 rounded-full bg-primary-600 animate-pulse-soft" />
            正在加载视频数据...
          </div>
        </div>
      ) : videos.length === 0 ? (
        <div className="panel p-10 text-center">
          <p className="text-lg font-semibold" style={{ color: 'var(--text-main)' }}>
            暂无视频
          </p>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-subtle)' }}>
            点击上方“导入收藏夹”开始构建知识库。
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
            {videos.map((video) => (
              <article key={video.bvid} className="card overflow-hidden">
                <div
                  className="h-32 px-4 py-3"
                  style={{
                    background:
                      'linear-gradient(130deg, rgba(11,136,209,0.20), rgba(22,168,245,0.06))',
                  }}
                >
                  <div className="badge-primary">{video.bvid}</div>
                </div>

                <div className="space-y-3 p-4">
                  <h3 className="text-base font-semibold" style={{ color: 'var(--text-main)' }}>
                    {video.title}
                  </h3>

                  <p className="text-sm" style={{ color: 'var(--text-subtle)' }}>
                    UP主：{video.owner_name || '未知'}
                  </p>

                  <p className="text-xs" style={{ color: 'var(--text-subtle)' }}>
                    播放量：{video.view_count?.toLocaleString() || 0}
                  </p>

                  <div className="flex gap-2">
                    <button className="btn-secondary btn-sm flex-1">详情</button>
                    <button onClick={() => handleDelete(video.bvid)} className="btn-danger btn-sm flex-1">
                      删除
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>

          <div className="panel p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm" style={{ color: 'var(--text-subtle)' }}>
                显示 {skip + 1}-{Math.min(skip + limit, total)} / 共 {total} 条
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setSkip(Math.max(0, skip - limit))}
                  disabled={skip === 0}
                  className="btn-secondary btn-sm"
                >
                  上一页
                </button>
                <button
                  onClick={() => setSkip(skip + limit)}
                  disabled={skip + limit >= total}
                  className="btn-secondary btn-sm"
                >
                  下一页
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
