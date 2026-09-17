const API_BASE = '/api'

export { API_BASE }

/**
 * fetch com cookie de sessão; redireciona para login em 401 (exceto rotas públicas).
 */
export async function apiFetch(path, options = {}) {
  const url = path.startsWith('/api') ? path : `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`
  const method = String(options.method || 'GET').toUpperCase()
  const isMutating = ['POST', 'PUT', 'PATCH'].includes(method)
  const hasBody = options.body != null && options.body !== ''
  const body = hasBody
    ? options.body
    : (isMutating ? '{}' : undefined)
  const sendJson = body != null && !(body instanceof FormData)

  const response = await fetch(url, {
    credentials: 'include',
    ...options,
    ...(body !== undefined ? { body } : {}),
    headers: {
      ...(sendJson ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  })

  if (response.status === 401 && !url.includes('/auth/login') && !url.includes('/auth/status')) {
    window.dispatchEvent(new CustomEvent('auth:required'))
  }

  return response
}

export async function apiJson(path, options = {}) {
  const response = await apiFetch(path, options)
  const data = await response.json().catch(() => ({}))
  return { response, data }
}
