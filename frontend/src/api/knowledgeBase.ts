import { http } from './http'

export interface KnowledgeBase {
  id: number
  name: string
  created_at: string
}

export const listKnowledgeBases = async () => {
  const res = await http.get<KnowledgeBase[]>('/knowledge-bases')
  return res.data
}

export const createKnowledgeBase = async (name: string) => {
  const res = await http.post<KnowledgeBase>('/knowledge-bases', { name })
  return res.data
}

export const deleteKnowledgeBase = async (id: number) => {
  const res = await http.delete(`/knowledge-bases/${id}`)
  return res.data
}
