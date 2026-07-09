import { http } from './http'

export const uploadDocument = async (file: File, knowledgeBaseId: number) => {
  const formData = new FormData()
  formData.append('file', file)

  const res = await http.post(
    `/documents/upload?knowledge_base_id=${knowledgeBaseId}`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    },
  )

  return res.data
}

export interface DocumentItem {
  id: number
  filename: string
  size: string
  created_at: string
  knowledge_base_id: number
  status: string
  error_message: string | null
  vector_count: number
}

export interface DocumentListResponse {
  items: DocumentItem[]
  total: number
  page: number
  page_size: number
}

export interface DocumentQueryParams {
  knowledgeBaseId: number
  page?: number
  pageSize?: number
  search?: string
  status?: string
}

export const getDocuments = async (
  params: DocumentQueryParams,
): Promise<DocumentListResponse> => {
  const res = await http.get<DocumentListResponse>('/documents', {
    params: {
      knowledge_base_id: params.knowledgeBaseId,
      page: params.page ?? 1,
      page_size: params.pageSize ?? 20,
      ...(params.search ? { search: params.search } : {}),
      ...(params.status ? { status: params.status } : {}),
    },
  })
  return res.data
}

export interface DocumentStatus {
  id: number
  status: string
  vector_count: number
  error_message: string | null
}

export const getDocumentStatuses = async (
  knowledgeBaseId: number,
  ids: number[],
): Promise<DocumentStatus[]> => {
  if (ids.length === 0) return []
  const res = await http.get<DocumentStatus[]>('/documents/status', {
    params: { knowledge_base_id: knowledgeBaseId, ids: ids.join(',') },
  })
  return res.data
}

export const reindexDocument = async (id: number) => {
  const res = await http.post(`/documents/${id}/reindex`)
  return res.data
}

export const deleteDocument = async (id: number) => {
  const res = await http.delete(`/documents/${id}`)
  return res.data
}

export const batchDeleteDocuments = async (ids: number[]) => {
  const res = await http.post('/documents/batch-delete', { ids })
  return res.data
}
