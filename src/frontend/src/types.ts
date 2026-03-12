// 前端 TypeScript 类型定义

export interface StockQuote {
  code: string
  name: string
  price: number
  open_price: number
  high_price: number
  low_price: number
  change_pct: number
  volume: number
  sector: string
}

export interface KlineBar {
  timestamp: number
  time_str: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface DepthLevel {
  price: number
  quantity: number
}

export interface DepthData {
  buy: DepthLevel[]
  sell: DepthLevel[]
}

export interface ChatMessage {
  agent_id: string
  agent_name: string
  content: string
  round_number: number
  virtual_time: string
  timestamp: number
}

export interface NewsEvent {
  news_id: string
  title: string
  content: string
  sentiment: string
  affected_stocks: string[]
  round_number: number
  virtual_time: string
}

export interface AgentPosition {
  agent_id: string
  agent_name: string
  agent_type: string
  cash: number
  positions: Record<string, number>
  total_value: number
  pnl_pct: number
}

export interface MarketSnapshot {
  round_number: number
  virtual_time: string
  timestamp: number
  stocks: Record<string, StockQuote>
}

export interface WSEvent {
  type: string
  data: any
}
