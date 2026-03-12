// REST + WebSocket 客户端封装
import type { MarketSnapshot, KlineBar, DepthData, ChatMessage, NewsEvent, AgentPosition } from './types'

const API_BASE = '/api'

// ========== REST 请求 ==========

export async function fetchSnapshot(): Promise<MarketSnapshot> {
  const res = await fetch(`${API_BASE}/market/snapshot`)
  return res.json()
}

export async function fetchKlines(code: string, limit = 100): Promise<KlineBar[]> {
  const res = await fetch(`${API_BASE}/market/klines/${code}?limit=${limit}`)
  return res.json()
}

export async function fetchDepth(code: string, levels = 5): Promise<DepthData> {
  const res = await fetch(`${API_BASE}/market/depth/${code}?levels=${levels}`)
  return res.json()
}

export async function fetchPositions(): Promise<AgentPosition[]> {
  const res = await fetch(`${API_BASE}/agents/positions`)
  return res.json()
}

export async function fetchMessages(limit = 50): Promise<ChatMessage[]> {
  const res = await fetch(`${API_BASE}/social/messages?limit=${limit}`)
  return res.json()
}

export async function fetchNews(limit = 20): Promise<NewsEvent[]> {
  const res = await fetch(`${API_BASE}/news?limit=${limit}`)
  return res.json()
}

export async function fetchStatus(): Promise<any> {
  const res = await fetch(`${API_BASE}/status`)
  return res.json()
}

export async function pauseSimulation(): Promise<void> {
  await fetch(`${API_BASE}/control/pause`, { method: 'POST' })
}

export async function resumeSimulation(): Promise<void> {
  await fetch(`${API_BASE}/control/resume`, { method: 'POST' })
}

// ========== WebSocket ==========

export function connectWebSocket(onEvent: (type: string, data: any) => void): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws`)

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      onEvent(msg.type, msg.data)
    } catch (e) {
      console.error('WebSocket 消息解析失败:', e)
    }
  }

  ws.onclose = () => {
    console.log('WebSocket 断开，3秒后重连...')
    setTimeout(() => connectWebSocket(onEvent), 3000)
  }

  ws.onerror = (e) => {
    console.error('WebSocket 错误:', e)
  }

  return ws
}
