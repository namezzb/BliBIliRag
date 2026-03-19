import { useState, useEffect } from 'react'
import { apiClient, Video } from '@/services/api'

export default function VideosPage() {
  const [videos, setVideos] = useState<Video[]>([])
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const limit = 20

  useEffect(() => {
    loadVideos()
  }, [skip])

  const loadVideos = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiClient.getVideos(skip, limit)
      setVideos(data.videos)
      setTotal(data.total)
    } catch (err) {
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
    const favoriteId = prompt('请输入收藏夹ID:')
    if (!favoriteId) return

    try {
      const task = await apiClient.importVideos(favoriteId)
      alert(`导入任务已创建: ${task.task_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import videos')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">视频库</h2>
        <button
          onClick={handleImport}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          导入收藏夹
        </button>
      </div>

      {/* Error message */}
      {error && (
        <div className="p-4 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg">
          {error}
        </div>
      )}

      {/* Videos grid */}
      {loading ? (
        <div className="text-center py-12">加载中...</div>
      ) : videos.length === 0 ? (
        <div className="text-center py-12 text-gray-500">暂无视频</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {videos.map((video) => (
              <div
                key={video.bvid}
                className="bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-lg transition-shadow overflow-hidden"
              >
                <div className="p-4">
                  <h3 className="font-semibold text-gray-900 dark:text-white truncate">{video.title}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {video.owner_name} • {video.view_count?.toLocaleString()} 次观看
                  </p>
                  <div className="mt-4 flex gap-2">
                    <button className="flex-1 px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
                      详情
                    </button>
                    <button
                      onClick={() => handleDelete(video.bvid)}
                      className="flex-1 px-3 py-1 text-sm bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded hover:bg-red-200 dark:hover:bg-red-800 transition-colors"
                    >
                      删除
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              显示 {skip + 1}-{Math.min(skip + limit, total)} / 共 {total} 个视频
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setSkip(Math.max(0, skip - limit))}
                disabled={skip === 0}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                上一页
              </button>
              <button
                onClick={() => setSkip(skip + limit)}
                disabled={skip + limit >= total}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                下一页
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
