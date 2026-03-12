// 盘口五档组件
import { useStore } from '../stores/useStore'

export default function OrderBookPanel() {
  const selectedStock = useStore((s) => s.selectedStock)
  const depth = useStore((s) => s.depth[s.selectedStock])
  const quote = useStore((s) => s.stocks[s.selectedStock])

  if (!depth) {
    return <div className="order-book-panel"><p className="empty">暂无盘口数据</p></div>
  }

  return (
    <div className="order-book-panel">
      <h3>盘口 - {quote?.name || selectedStock}</h3>
      <div className="depth-table">
        <div className="depth-section sell-section">
          <div className="depth-header">
            <span>卖出价</span><span>数量</span>
          </div>
          {[...depth.sell].reverse().map((level, i) => (
            <div key={`sell-${i}`} className="depth-row sell">
              <span className="price sell-price">¥{level.price.toFixed(2)}</span>
              <span className="qty">{level.quantity}</span>
            </div>
          ))}
        </div>
        <div className="current-price">
          <span className={`price ${quote && quote.change_pct >= 0 ? 'up' : 'down'}`}>
            ¥{quote?.price.toFixed(2) || '--'}
          </span>
          <span className={`change ${quote && quote.change_pct >= 0 ? 'up' : 'down'}`}>
            {quote ? `${quote.change_pct >= 0 ? '+' : ''}${quote.change_pct.toFixed(2)}%` : ''}
          </span>
        </div>
        <div className="depth-section buy-section">
          <div className="depth-header">
            <span>买入价</span><span>数量</span>
          </div>
          {depth.buy.map((level, i) => (
            <div key={`buy-${i}`} className="depth-row buy">
              <span className="price buy-price">¥{level.price.toFixed(2)}</span>
              <span className="qty">{level.quantity}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
