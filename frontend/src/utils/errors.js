// Turns an axios error into a message a person can act on.
export function describeError(err, fallback = 'Something went wrong.') {
  if (!err) return fallback
  if (!err.response) {
    return "Can't reach the server. Check that the backend is running, then try again."
  }
  const detail = err.response.data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (err.response.status >= 500) return 'The server ran into a problem. Try again in a moment.'
  return fallback
}

export const isNetworkError = (err) => !!err && !err.response
