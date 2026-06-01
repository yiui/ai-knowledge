import { API_BASE_URL } from '@/config'
import { getToken } from '@/stores/auth'

import { http } from './http'

export const chatApi = async (
  question: string,
  knowledgeBaseId?: number | null,
) => {
  const res = await http.post('/chat', {
    question,
    knowledge_base_id: knowledgeBaseId ?? null,
  })

  return res.data
}

export const chatStreamApi = async (
  question: string,
  onChunk: (text: string) => void,
  knowledgeBaseId?: number | null,
): Promise<void> => {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      question,
      knowledge_base_id: knowledgeBaseId ?? null,
    }),
  })

  if (!response.ok) {
    throw new Error(`Chat stream failed: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('No response body')
  }

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue

      const data = line.slice(6).trim()
      if (data === '[DONE]') return

      const parsed = JSON.parse(data) as { text?: string }
      if (parsed.text) {
        onChunk(parsed.text)
      }
    }
  }
}

export function search(query: string, knowledgeBaseId: number) {
  return http.post('/search', { query, knowledge_base_id: knowledgeBaseId })
}
