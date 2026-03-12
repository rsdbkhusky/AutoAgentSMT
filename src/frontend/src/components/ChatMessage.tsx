// 单条聊天消息组件
import type { ChatMessage as ChatMsgType } from '../types'

const typeColors: Record<string, string> = {
  conservative: '#26a69a',
  aggressive: '#ef5350',
  follower: '#ffa726',
  value: '#42a5f5',
}

export default function ChatMessage({ msg }: { msg: ChatMsgType }) {
  // 从 agent_id 中提取类型
  const agentType = msg.agent_id.split('_')[0]
  const color = typeColors[agentType] || '#888'

  return (
    <div className="chat-message">
      <div className="msg-header">
        <span className="msg-name" style={{ color }}>{msg.agent_name}</span>
        <span className="msg-time">{msg.virtual_time}</span>
      </div>
      <div className="msg-content">{msg.content}</div>
    </div>
  )
}
