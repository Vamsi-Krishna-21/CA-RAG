const API_BASE =
  import.meta.env.VITE_API_URL ||
  'http://127.0.0.1:8000'

function getToken() {
  return (
    localStorage.getItem('carag_token') ||
    localStorage.getItem('token') ||
    localStorage.getItem('access_token') ||
    ''
  )
}

async function request(path, options = {}) {
  const token = getToken()

  const headers = {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (response.status === 401) {
    window.location.href = '/login'
    throw new Error('Authentication required')
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`

    try {
      const data = await response.json()
      message =
        data?.detail ||
        data?.message ||
        message
    } catch {
      // Keep the default message.
    }

    throw new Error(message)
  }

  if (response.status === 204) {
    return null
  }

  return response.json()
}

/* ---------------------------
   Conversation list
---------------------------- */

export async function listConversations() {
  return request('/api/conversations')
}

/* ---------------------------
   Create conversation
---------------------------- */

export async function createConversation({
  title = 'New chat',
  documentIds = [],
} = {}) {
  return request('/api/conversations', {
    method: 'POST',
    body: JSON.stringify({
      title,
      document_ids: documentIds,
    }),
  })
}

/* ---------------------------
   Get conversation
---------------------------- */

export async function getConversation(conversationId) {
  return request(
    `/api/conversations/${conversationId}`,
  )
}

/* ---------------------------
   Rename conversation
---------------------------- */

export async function renameConversation(
  conversationId,
  title,
) {
  return request(
    `/api/conversations/${conversationId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        title,
      }),
    },
  )
}

/* ---------------------------
   Pin / unpin
---------------------------- */

export async function togglePinConversation(
  conversationId,
) {
  return request(
    `/api/conversations/${conversationId}/pin`,
    {
      method: 'POST',
    },
  )
}

/* ---------------------------
   Archive / unarchive
---------------------------- */

export async function toggleArchiveConversation(
  conversationId,
) {
  return request(
    `/api/conversations/${conversationId}/archive`,
    {
      method: 'POST',
    },
  )
}

/* ---------------------------
   Delete conversation
---------------------------- */

export async function deleteConversation(
  conversationId,
) {
  return request(
    `/api/conversations/${conversationId}`,
    {
      method: 'DELETE',
    },
  )
}

/* ---------------------------
   Share conversation
---------------------------- */

export async function shareConversation(
  conversationId,
) {
  return request(
    `/api/conversations/${conversationId}/share`,
    {
      method: 'POST',
    },
  )
}