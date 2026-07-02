const configured = import.meta.env.VITE_API_BASE_URL?.trim()

// 生产 Docker 部署：VITE_API_BASE_URL 留空，走同域 Nginx 反代 /auth 等路径
// 本地开发：未配置时默认 localhost:8000
export const API_BASE_URL =
  configured || (import.meta.env.DEV ? 'http://localhost:8000' : '')

/** 启动时打印 API 配置，便于排查 Docker / 生产环境请求地址 */
export function logApiConfig() {
  const pageOrigin = typeof window !== 'undefined' ? window.location.origin : '(ssr)'
  console.info('[api-config]', {
    VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL ?? '(undefined)',
    API_BASE_URL: API_BASE_URL || '(empty, same-origin relative)',
    pageOrigin,
    mode: import.meta.env.MODE,
    dev: import.meta.env.DEV,
  })
}
