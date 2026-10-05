import client from './axiosClient'

export async function listDocuments() {
  const res = await client.get('/documents')
  return res.data
}

export async function uploadDocument(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await client.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (evt) => {
      if (onProgress) onProgress(Math.round((evt.loaded * 100) / evt.total))
    },
  })
  return res.data
}

export async function deleteDocument(id) {
  const res = await client.delete(`/documents/${id}`)
  return res.data
}
