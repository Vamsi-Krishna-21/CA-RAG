export default function UserMessage({ message }) {
  return (
    <div className="msg msg-user" id={message.id ? `m-${message.id}` : undefined}>
      <div className="user-bubble">{message.content.query}</div>
    </div>
  )
}
