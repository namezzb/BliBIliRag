import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import QRCode from 'qrcode'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface QRCodeResponse {
  status: string
  qrcode_key: string
  qrcode_url: string
}

interface PollResponse {
  status: string
  auth_code: number
  auth_message: string
  has_session: boolean
}

export default function LoginPage() {
  const navigate = useNavigate()
  const [qrcodeUrl, setQrcodeUrl] = useState<string | null>(null)
  const [qrcodeImage, setQrcodeImage] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [polling, setPolling] = useState(false)
  const [message, setMessage] = useState<string>('')

  const startPolling = (key: string) => {
    setPolling(true)
    let pollCount = 0
    const maxPolls = 150

    const interval = setInterval(async () => {
      pollCount++

      if (pollCount > maxPolls) {
        clearInterval(interval)
        setPolling(false)
        setError('登录超时，请重新生成二维码')
        setQrcodeUrl(null)
        setQrcodeImage(null)
        return
      }

      try {
        const response = await axios.get<PollResponse>(
          `${API_URL}/api/auth/qrcode/poll?qrcode_key=${key}`
        )

        const { auth_code: authCode, has_session: hasSession } = response.data

        if (hasSession || authCode === 0) {
          setMessage('登录成功，正在进入系统...')
          clearInterval(interval)
          setPolling(false)
          setTimeout(() => navigate('/'), 900)
        } else if (authCode === 86038) {
          setError('二维码已过期，请重新生成')
          clearInterval(interval)
          setPolling(false)
          setQrcodeUrl(null)
          setQrcodeImage(null)
        } else if (authCode === 86090) {
          setMessage('已扫码，请在手机端确认登录')
        } else if (authCode === 86101) {
          setMessage('二维码已生成，请使用 B站 APP 扫码')
        }
      } catch {
        // keep polling quietly
      }
    }, 2000)
  }

  const generateQRCode = async () => {
    try {
      setLoading(true)
      setError(null)
      setMessage('正在生成二维码...')

      const response = await axios.post<QRCodeResponse>(`${API_URL}/api/auth/qrcode/generate`, {})
      const qrImageDataUrl = await QRCode.toDataURL(response.data.qrcode_url, {
        width: 320,
        margin: 1,
      })
      setQrcodeUrl(response.data.qrcode_url)
      setQrcodeImage(qrImageDataUrl)
      setMessage('请使用 B站 APP 扫码确认登录')
      startPolling(response.data.qrcode_key)
    } catch (err) {
      const errorMsg = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : '生成二维码失败'
      setError(errorMsg)
      setMessage('')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const checkLogin = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/auth/me`)
        if (response.data.is_logged_in) {
          navigate('/')
        }
      } catch {
        // keep login page
      }
    }

    void checkLogin()
  }, [navigate])

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-xl space-y-4">
        <section className="panel p-7 sm:p-10 animate-fade-in">
          <div className="text-center">
            <div className="mx-auto mb-4 h-12 w-12 rounded-2xl flex items-center justify-center text-white font-bold"
              style={{ background: 'linear-gradient(120deg, #0b88d1, #16a8f5)' }}
            >
              BR
            </div>
            <h1 className="text-3xl font-bold" style={{ color: 'var(--text-main)' }}>
              B站收藏夹智能管理系统
            </h1>
            <p className="mt-2 text-sm" style={{ color: 'var(--text-subtle)' }}>
              扫码后进入联调仪表盘
            </p>
          </div>

          <div className="mt-7 space-y-5">
            {qrcodeUrl && qrcodeImage ? (
              <div className="space-y-4">
                <div className="panel-muted mx-auto w-fit p-3">
                  <img src={qrcodeImage} alt="B站登录二维码" className="h-64 w-64" />
                </div>
                <p className="text-center text-sm" style={{ color: 'var(--text-subtle)' }}>
                  {message}
                </p>
                {polling && (
                  <p className="text-center text-xs" style={{ color: 'var(--text-subtle)' }}>
                    正在轮询确认状态...
                  </p>
                )}
                <button onClick={() => void generateQRCode()} disabled={loading || polling} className="btn-secondary w-full">
                  {loading ? '生成中...' : '重新生成二维码'}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="panel-muted p-4 text-sm" style={{ color: 'var(--text-subtle)' }}>
                  1. 点击生成二维码。<br />
                  2. 使用 B站 APP 扫码。<br />
                  3. 确认授权后自动跳转。
                </div>

                <button onClick={() => void generateQRCode()} disabled={loading} className="btn-primary w-full">
                  {loading ? '生成中...' : '生成二维码'}
                </button>
              </div>
            )}

            {error && (
              <div className="rounded-xl px-4 py-3 text-sm" style={{ color: '#a92929', background: '#fff1f1', border: '1px solid #f5bcbc' }}>
                {error}
              </div>
            )}
          </div>
        </section>

        <p className="text-center text-xs" style={{ color: 'var(--text-subtle)' }}>
          v0.1.0 · Powered by FastAPI + React
        </p>
      </div>
    </div>
  )
}
