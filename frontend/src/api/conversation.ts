import { API_BASE_URL } from '@/config'
import { getToken } from '@/stores/auth'

import { http } from './http'

export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface ConversationSummary {
  id: number
  title: string
  knowledge_base_id: number | null
  message_count: number
  max_messages: number
  should_start_new: boolean
  created_at: string
  updated_at: string
}

export interface ConversationDetail extends ConversationSummary {
  messages: Message[]
}

export interface ChatLimits {
  max_messages_per_conversation: number
}

export const getChatLimits = async () => {
  const res = await http.get<ChatLimits>('/conversations/limits')
  return res.data
}

export const listConversations = async () => {
  const res = await http.get<ConversationSummary[]>('/conversations')
  return res.data
}

export const createConversation = async (payload?: {
  title?: string
  knowledge_base_id?: number | null
}) => {
  const res = await http.post<ConversationSummary>('/conversations', payload ?? {})
  return res.data
}

export const getConversation = async (id: number) => {
  const res = await http.get<ConversationDetail>(`/conversations/${id}`)
  return res.data
}

export const updateConversation = async (
  id: number,
  payload: { title?: string; knowledge_base_id?: number | null },
) => {
  const res = await http.patch<ConversationSummary>(`/conversations/${id}`, payload)
  return res.data
}

export const deleteConversation = async (id: number) => {
  const res = await http.delete(`/conversations/${id}`)
  return res.data
}

export interface StreamDoneMeta {
  done: true
  message_count: number
  max_messages: number
  should_start_new: boolean
}

export interface SourceMeta {
  filename: string
  chunk_index: number
  chunk_total: number
}

export interface StreamSources {
  sources: SourceMeta[]
}

export const chatStreamInConversation = async (
  conversationId: number,
  question: string,
  onChunk: (text: string) => void,
  onSources?: (sources: SourceMeta[]) => void,
  onDone?: (meta: StreamDoneMeta) => void,
): Promise<void> => {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(
    `${API_BASE_URL}/conversations/${conversationId}/chat/stream`,
    {
      method: 'POST',
      headers,
      body: JSON.stringify({ question }),
    },
  )

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    const detail = (err as { detail?: string }).detail
    throw new Error(detail || `Chat stream failed: ${response.status}`)
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

      const parsed = JSON.parse(data) as { text?: string; done?: boolean; sources?: SourceMeta[] }
      if (parsed.sources && onSources) {
        onSources(parsed.sources)
      }
      if (parsed.text) {
        onChunk(parsed.text)
      }
      if (parsed.done && onDone) {
        onDone(parsed as StreamDoneMeta)
      }
    }
  }
}
