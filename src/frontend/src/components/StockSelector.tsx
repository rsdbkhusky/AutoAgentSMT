// 股票切换选择器
import { useStore } from '../stores/useStore'

export default function StockSelector() {
  const stocks = useStore((s) => s.stocks)
  const selectedStock = useStore((s) => s.selectedStock)

  const stockList = Object.values(stocks).sort((a, b) => a.code.localeCompare(b.code))

  return (
    <div className="stock-selector">
      <select
        value={selectedStock}
        onChange={(e) => useStore.getState().setSelectedStock(e.target.value)}
      >
        {stockList.map((s) => (
          <option key={s.code} value={s.code}>
            {s.name} ({s.code}) ¥{s.price.toFixed(2)} {s.change_pct >= 0 ? '+' : ''}{s.change_pct.toFixed(2)}%
          </option>
        ))}
      </select>
    </div>
  )
}
