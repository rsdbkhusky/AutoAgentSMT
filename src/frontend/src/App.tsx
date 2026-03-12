// 根组件
import { useEffect, useRef } from 'react'
import { useStore } from './stores/useStore'
import { connectWebSocket, fetchSnapshot, fetchMessages, fetchNews, fetchPositions, fetchKlines, fetchDepth, fetchStatus } from './api'
import StatusBar from './components/StatusBar'
import TaskBar from './components/TaskBar'
import TradeTerminal from './components/TradeTerminal'
import ChatRoom from './components/ChatRoom'
import NewsPanel from './components/NewsPanel'

// 拉取所有数据的通用函数
async function refreshAllData() {
  const store = useStore.getState()
  try {
    const [snapshot, messages, news, positions, status] = await Promise.all([
      fetchSnapshot(),
      fetchMessages(),
      fetchNews(),
      fetchPositions(),
      fetchStatus(),
    ])
    store.updateMarket(snapshot)
    store.setMessages(messages)
    store.setNews(news)
    store.setPositions(positions)
    store.setRoundInfo(status.round_number, status.virtual_time)
    store.setStatus(status.status)
    // 设置默认选中股票
    const codes = Object.keys(snapshot.stocks || {})
    if (codes.length > 0 && !store.selectedStock) {
      store.setSelectedStock(codes[0])
    }
    // 刷新当前选中股票的K线和盘口
    const code = store.selectedStock
    if (code) {
      const [klines, depth] = await Promise.all([fetchKlines(code), fetchDepth(code)])
      store.setKlines(code, klines)
      store.updateDepth(code, depth)
    }
  } catch (e) {
    console.error('数据加载失败:', e)
  }
}

export default function App() {
  const activePanel = useStore((s) => s.activePanel)
  const selectedStock = useStore((s) => s.selectedStock)
  const pollRef = useRef<number | null>(null)

  useEffect(() => {
    // 初始化加载
    refreshAllData()

    // 定时轮询（作为 WebSocket 的保底方案，每5秒刷新一次）
    pollRef.current = window.setInterval(refreshAllData, 5000)

    // 尝试建立 WebSocket 连接（成功后实时推送会更快）
    const ws = connectWebSocket((type, data) => {
      const store = useStore.getState()
      switch (type) {
        case 'market_update':
          store.updateMarket(data)
          break
        case 'round_start':
          store.setRoundInfo(data.round_number, data.virtual_time)
          store.setStatus('running')
          break
        case 'round_end':
          store.setRoundInfo(data.round_number, data.virtual_time)
          // 回合结束时拉取最新K线和盘口
          if (store.selectedStock) {
            fetchKlines(store.selectedStock).then(bars => store.setKlines(store.selectedStock, bars))
            fetchDepth(store.selectedStock).then(d => store.updateDepth(store.selectedStock, d))
          }
          break
        case 'chat':
          store.addMessage(data)
          break
        case 'news':
          store.addNews(data)
          break
        case 'agent_update':
          store.setPositions(data)
          break
      }
    })

    return () => {
      ws.close()
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  // 切换股票时拉取对应数据
  useEffect(() => {
    if (!selectedStock) return
    fetchKlines(selectedStock).then(bars => useStore.getState().setKlines(selectedStock, bars))
    fetchDepth(selectedStock).then(d => useStore.getState().updateDepth(selectedStock, d))
  }, [selectedStock])

  return (
    <div className="app">
      <StatusBar />
      <div className="main-content">
        {activePanel === 'trade' && <TradeTerminal />}
        {activePanel === 'chat' && <ChatRoom />}
        {activePanel === 'news' && <NewsPanel />}
      </div>
      <TaskBar />
    </div>
  )
}
