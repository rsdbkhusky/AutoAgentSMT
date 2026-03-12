// Zustand 全局状态管理
import { create } from 'zustand'
import type { StockQuote, KlineBar, DepthData, ChatMessage, NewsEvent, AgentPosition } from '../types'

export type PanelType = 'trade' | 'chat' | 'news'

interface AppState {
  // UI 状态
  activePanel: PanelType
  selectedStock: string

  // 市场数据
  virtualTime: string
  roundNumber: number
  status: string
  stocks: Record<string, StockQuote>
  klines: Record<string, KlineBar[]>
  depth: Record<string, DepthData>
  positions: AgentPosition[]
  messages: ChatMessage[]
  news: NewsEvent[]

  // 操作
  setActivePanel: (panel: PanelType) => void
  setSelectedStock: (code: string) => void
  setStatus: (s: string) => void
  updateMarket: (data: any) => void
  addKline: (code: string, bar: KlineBar) => void
  setKlines: (code: string, bars: KlineBar[]) => void
  updateDepth: (code: string, data: DepthData) => void
  setPositions: (p: AgentPosition[]) => void
  addMessage: (msg: ChatMessage) => void
  setMessages: (msgs: ChatMessage[]) => void
  addNews: (n: NewsEvent) => void
  setNews: (list: NewsEvent[]) => void
  setRoundInfo: (round: number, time: string) => void
}

export const useStore = create<AppState>((set) => ({
  activePanel: 'trade',
  selectedStock: '',
  virtualTime: '',
  roundNumber: 0,
  status: 'stopped',
  stocks: {},
  klines: {},
  depth: {},
  positions: [],
  messages: [],
  news: [],

  setActivePanel: (panel) => set({ activePanel: panel }),
  setSelectedStock: (code) => set({ selectedStock: code }),
  setStatus: (s) => set({ status: s }),

  updateMarket: (data) => set((state) => ({
    stocks: data.stocks || state.stocks,
    virtualTime: data.virtual_time || state.virtualTime,
    roundNumber: data.round_number ?? state.roundNumber,
  })),

  addKline: (code, bar) => set((state) => ({
    klines: {
      ...state.klines,
      [code]: [...(state.klines[code] || []), bar],
    },
  })),

  setKlines: (code, bars) => set((state) => ({
    klines: { ...state.klines, [code]: bars },
  })),

  updateDepth: (code, data) => set((state) => ({
    depth: { ...state.depth, [code]: data },
  })),

  setPositions: (p) => set({ positions: p }),

  addMessage: (msg) => set((state) => ({
    messages: [...state.messages.slice(-200), msg],
  })),

  setMessages: (msgs) => set({ messages: msgs }),

  addNews: (n) => set((state) => ({
    news: [n, ...state.news].slice(0, 100),
  })),

  setNews: (list) => set({ news: list }),

  setRoundInfo: (round, time) => set({ roundNumber: round, virtualTime: time }),
}))
