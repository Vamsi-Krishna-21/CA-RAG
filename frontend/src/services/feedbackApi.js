import client from './axiosClient'

export async function sendFeedback(messageId, rating, usedChunks) {
  const res = await client.post('/feedback', {
    message_id: messageId,
    rating,
    used_chunks: usedChunks,
  })
  return res.data
}
