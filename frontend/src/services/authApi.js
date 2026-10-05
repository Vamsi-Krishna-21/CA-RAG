import client from './axiosClient'

export async function register(name, email, password, username) {
  const body = { name, email, password }
  if (username) body.username = username
  const res = await client.post('/auth/register', body)
  return res.data
}

// `identifier` is an email or a username.
export async function login(identifier, password) {
  const res = await client.post('/auth/login', { identifier, password })
  return res.data
}

export async function getMe() {
  const res = await client.get('/auth/me')
  return res.data
}

export async function forgotPassword(email) {
  const res = await client.post('/auth/forgot-password', { email })
  return res.data
}

export async function resetPassword(token, password) {
  const res = await client.post(`/auth/reset-password/${encodeURIComponent(token)}`, { password })
  return res.data
}
