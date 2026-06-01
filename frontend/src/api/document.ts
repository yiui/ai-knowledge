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

export const getDocuments = async (knowledgeBaseId: number) => {
  const res = await http.get('/documents', {
    params: { knowledge_base_id: knowledgeBaseId },
  })
  return res.data
}

export const deleteDocument = async (id: number) => {
  const res = await http.delete(`/documents/${id}`)
  return res.data
}
