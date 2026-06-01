import { http } from './http'

export const uploadDocument = async (file: File) => {
  const formData = new FormData()

  formData.append('file', file)

  const res = await http.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return res.data
}

export const getDocuments = async () => {
  const res = await http.get('/documents')
  return res.data
}

export const deleteDocument = async (id: number) => {
  const res = await http.delete(`/documents/${id}`)
  return res.data
}
