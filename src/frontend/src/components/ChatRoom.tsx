// 群聊面板
import { useEffect, useRef } from 'react'
import { useStore } from '../stores/useStore'
import ChatMessage from './ChatMessage'

export default function ChatRoom() {
  const messages = useStore((s) => s.messages)
  const bottomRef = useRef<HTMLDivElement>(null)

  // 自动滚动到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  return (
    <div className="chat-room">
      <h2>交流群</h2>
      <div className="chat-list">
        {messages.length === 0 && <p className="empty">暂无消息，等待Agent发言...</p>}
        {messages.map((msg, i) => (
          <ChatMessage key={`${msg.agent_id}-${msg.timestamp}-${i}`} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
