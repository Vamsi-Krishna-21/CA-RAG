# CA-RAG frontend redesign

Frontend only. `src/services/**`, `src/context/**`, `ProtectedRoute.jsx`, `main.jsx`,
`package.json` and `vite.config.js` are unchanged: no API, auth or backend change, and no new dependencies.

## Structure
```
src/
  components/ layout/ sidebar/ chat/ verification/ citations/ feedback/ documents/ common/
  hooks/      useDocuments (shared list + polling), useUpload, useDismiss, useLocalStorage
  utils/      dates, errors, messages, verification
  styles/     tokens (light/dark), base, shell, chat, verification, pages
  pages/      Chat, Documents, History, Settings, Login, Register, ForgotPassword, ResetPassword
```
Routes: `/` and `/chat` -> Chat, `/documents`, `/history`, `/settings` (inside one persistent shell). The old Dashboard page was retired.

## What the UI shows, and where the data comes from
- Answer, confidence, status, hallucination risk, sources, evidence similarity: exactly the values the API returns.
- Hallucination-risk *label* (Low / Moderate / High) is derived from the API `status`; the percentage is `hallucination_risk`.
- Pipeline list: which steps run in the selected mode. The API does not report per-step results.
- Past answers do not know their mode (the backend does not store it); it is remembered per message in this browser.
- No file size and no "Open" button: the API provides neither. "New chat" returns to the document picker (history is one thread per document).

## Fixes made along the way
- Feedback buttons now also appear on answers loaded from history.
- A failed request shows an error with Retry instead of a fake "insufficient evidence" answer.
- Server timestamps (UTC without a suffix) are parsed as UTC.
- Deleting a document asks for confirmation.

## Run
    npm install && npm run dev      # or: npm run build
